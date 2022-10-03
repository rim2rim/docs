import urllib3
import json
import urllib
import boto3
import base64
from botocore.exceptions import ClientError
from botocore.config import Config
import configparser


def get_secret():
    secret_name = "SiteServicesBot"
    region_name = "us-east-1"
    secret=""
   
    # Create a Secrets Manager client
   
     
    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        print("Got the boto3 session")
        
        my_config = Config(retries = dict(max_attempts = 2),region_name='us-east-1')
        print("Setting config with retry 2 ")
        
        client = session.client('secretsmanager', config=my_config)
        print("Got secrets manager client")
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        print("Got secrets value")
    except Exception as e:
            print(e)
            raise(e)            
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            
            
    return secret        

def getchannelmembers(channelid,slacktoken):
    channelmembers=[ ]
    data = {'channel': channelid}
    header={'Authorization': 'Bearer '+slacktoken}
    #Checking whether the user is member of ssbot-fastgroup
    url = 'https://slack.com/api/conversations.members?channel='+channelid
    print(channelid)
     
    try:
        resp=sendhttprequest(data,'GET',header,url)
        response_json=json.loads(resp.data.decode('utf-8'))
        #print(response_json)
        channelmembers= response_json["members"]
        #print(channelmembers)
    except Exception as e:
        print(e)  
        raise e 
    return channelmembers
    
def getuserdetails(userid,slacktoken):
    url = 'https://slack.com/api/users.info?user='+userid
    data = {'attribute': 'value'}
    header={'Authorization': 'Bearer '+slacktoken}

    print(url)
    try:
      resp=sendhttprequest(data,'GET',header,url)
      userdetails=json.loads(resp.data.decode('utf-8'))
    except Exception as e:     
      print(" I am here...")     
      print(e)  
    return userdetails


def sendhttprequest(body,mode,header,url):
    try:
        http = urllib3.PoolManager()
        encoded_data = json.dumps(body).encode('utf-8')
        resp = http.request(mode, url,body=encoded_data,headers=header,timeout=3.0)         
    except Exception as e:
        print(e)
        raise e         
    return resp


#def checkinventories(towertoken, url):
#    tower_data = {   }        
#    header={'Authorization': 'Bearer '+towertoken, 'Content-Type': 'application/json'}
#Added for AWX
def checkinventories(awxtoken, url):
    tower_data = {   }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    
    try:
      resp=sendhttprequest(tower_data,'GET',header,url)
      #print(resp)
    except Exception as e:
        
        print(e)  
        raise(e)
    response_json=json.loads(resp.data.decode('utf-8'))
    #print(response_json)
    return response_json


def approve_TWRjob(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['approv_jb_num']
    print(devicename)
   
    

    try:
        secrets=json.loads(get_secret())
    except Exception as e:  
       print(e)      
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to set secrets from AWS, please try again later"
                     },
                   }
                 }    
         
       return response
         
    #Pull token from the SecretManager
    #slacktoken=secrets['slacktoken']
    slacktoken=secrets['approv_slack_token']
    
    
    
    #Lets first check if the user is eligible
    
     


       
       
    try:
       eligiblefunctionalities=get_eligible_functionalities(userid,slacktoken)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to contact Slack for channel details, please try again later"
                     },
                }
          }    
        print(e)  
        return response
         
     
     
    # We will use the above to figure out if the member is authorized to do this work
    if not any("Approve.action-APPROVE" in s for s in eligiblefunctionalities):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to APPROVE this Job. You should be a member of automation-alert channel. Contact Steve Humphrey."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
#    towertoken=secrets['tower_ss_token']  
    #Add awx token from SecretManager
    awxtoken=secrets['awx_ss_token'] 
    
    userdetails = []
    try:   
      userdetails  = getuserdetails(userid,slacktoken)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to contact Slack for Email id , please try again later"
                     },
                }
          }    
        print(e)  
        return response

    emailid=userdetails["user"]["profile"]["email"]
    print(emailid)
    id=devicename
    print(id)
    tower_data={'name': 'Approve AP Reboot', 'description': 'Approval for AP Reboot'}
#    header={'Authorization': 'Bearer '+towertoken, 'Content-Type': 'application/json'}
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    print(header)
    url = 'https://awx.managed.karops.io/api/v2/workflow_approvals/'+ id + '/approve/'
#    url = 'https://tower.karops.io/api/v2/workflow_approvals/'+ id + '/approve/'
    print(url)
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    #response_json=json.loads(resp.data.decode('utf-8'))
    #print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Approval submitted for "+devicename+". Remaining tasks will be completed shortly"
            },
        }
    }


    return response


def deny_TWRjob(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['deny_jb_num']
    print(devicename)
   
    

    try:
        secrets=json.loads(get_secret())
    except Exception as e:  
       print(e)      
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to set secrets from AWS, please try again later"
                     },
                   }
                 }    
         
       return response
         
    #Pull token from the SecretManager
    #slacktoken=secrets['slacktoken']
    slacktoken=secrets['approv_slack_token']
    
    
    
    #Lets first check if the user is eligible
    
     


       
       
    try:
       eligiblefunctionalities=get_eligible_functionalities(userid,slacktoken)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to contact Slack for channel details, please try again later"
                     },
                }
          }    
        print(e)  
        return response
         
     
     
    # We will use the above to figure out if the member is authorized to do this work
    if not any("Deny.action-DENY" in s for s in eligiblefunctionalities):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to DENY this Job. You should be a member of automation-alert channel. Contact Steve Humphrey."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
#    towertoken=secrets['tower_ss_token']  
    #Add awx token from SecretManager
    awxtoken=secrets['awx_ss_token'] 
    
    userdetails = []
    try:   
      userdetails  = getuserdetails(userid,slacktoken)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to contact Slack for Email id , please try again later"
                     },
                }
          }    
        print(e)  
        return response

    emailid=userdetails["user"]["profile"]["email"]
    print(emailid)
    id=devicename
    print(id)
    tower_data={'name': 'Approve AP Reboot', 'description': 'Approval for AP Reboot'}
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
#    header={'Authorization': 'Bearer '+towertoken, 'Content-Type': 'application/json'}
    print(header)
    url = 'https://awx.managed.karops.io/api/v2/workflow_approvals/'+ id + '/deny/'
#    url = 'https://tower.karops.io/api/v2/workflow_approvals/'+ id + '/deny/'
    print(url)
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    #response_json=json.loads(resp.data.decode('utf-8'))
    #print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "DENY was submitted for "+devicename+". No Remaining tasks exist"
            },
        }
    }


    return response


def get_eligible_functionalities(userid,slacktoken):
    config = configparser.ConfigParser()
    config.read('ssapprov.ini')
    authorisedset = set()  
    try:
       for name  in config['ssapprovpref']:
         if any(userid in s for s in getchannelmembers(name.upper(),slacktoken)):  
            string_value = config['ssapprovpref'][name]
            x = string_value.split(",")
            for i in x:                               
              authorisedset.add(i)  

       print(authorisedset) 

    except Exception as e:
      print(e)
      raise(e)  
    return authorisedset
  


def show_help_response_card(event, context):
    print(event)
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    userid ='UEK70S31B'
    secrets=json.loads(get_secret())
    #Pull token from the SecretManager
    slacktoken=secrets['approv_slack_token']
    
    
    #print(slacktoken)
    #Lets first check if the user is eligible     
    #Checking whether the user is member of ssbot-fastgroup   
    authorisedset = set()  
     

     
    try:
      authorisedset=get_eligible_functionalities(userid,slacktoken)
    except Exception as e:
        print(e) 
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to contact Slack for channel details, please try again later"
                     },
                }
          }            
        return response  
        

    buttonarray=[ ]
    index=0
    for val in authorisedset: 
        splitresults= val.split("-")

        dict = {"text": splitresults[1], "value": splitresults[0]}
        print(val) 
        buttonarray.append(dict)
        index = index + 1 
    print(buttonarray)
    if not buttonarray:
       buttonarray=[{"text":"No Access. Contact Steve Humphrey","value":"help"}] 
      
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                 "contentType": "SSML",
                 "content": "Action"
                 },
            "responseCard": {
                "version": "2",
                "contentType": "application/vnd.amazonaws.card.generic",
                "genericAttachments": [
                      {
                'title': 'SSSTEVE',
                'subTitle': 'sssteve action',
                 
                "buttons": buttonarray
                }
                ] 
            }
        }

        }
    
    


    return response


def lambda_handler(event, context):
   
    intentname=event["currentIntent"]['name']
    print(intentname)

    if intentname == "TowerApproval":
       return approve_TWRjob(event, context)
    elif intentname == "TowerDeny":
       return deny_TWRjob(event, context)
    elif intentname == "approveHelp":
       return show_help_response_card(event, context)    
     
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Invalid Intent"
            },
        }
    }
    
    return response