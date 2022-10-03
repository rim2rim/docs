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
     


def aruba_handler(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['device_name']
    print(devicename)
    location=event["currentIntent"]['slots']['location']
    print(location)
   
    

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
    slacktoken=secrets['slacktoken']
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
    print(eligiblefunctionalities)
    if not any("Aruba.help+Reboot AP" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Reboot Aruba WLC's. Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/170/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for checking "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }
     
    
    return response  

def showAP_uptime(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['controller_name']
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
    slacktoken=secrets['slacktoken']
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
         
     
    print(eligiblefunctionalities) 
    # We will use the above to figure out if the member is authorized to do this work
    if not any("ShowAp.help+Show AP Uptime" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to view Show ARUBA AP uptime. Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
    #towertoken=secrets['tower_ss_token']  
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
    tower_data = { "extra_vars": { "cli": devicename } }        
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/167/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for Show AP Uptime on "+devicename+". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response
 
def restart_spooler(event, context):
    print(event)
     
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['server']
    print(devicename)
    location=event["currentIntent"]['slots']['location']
    print(location) 
   
    

    secrets=json.loads(get_secret())
    #Pull token from the SecretManager
    slacktoken=secrets['slacktoken']
    #Lets first check if the user is eligible

    eligiblefunctionalities=get_eligible_functionalities(userid,slacktoken)
    
    print(eligiblefunctionalities) 
    # We will use the above to figure out if the member is authorized to do this work
    if not any("Restart.help+Restart Print Spooler" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Print Spooler Restart. Contact Site Services."
                     },
                }
          }    
       return  response


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

    #Pull token from the SecretManager
    awxtoken=secrets['awx_ss_token']
 

    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"ss_requestor": emailid  } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/173/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for Restarting PrintServer: "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }

    return response

def port_guestvlan(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['switch_name']
    print(devicename)
    portnum=event["currentIntent"]['slots']['port_num']
    print(portnum)
    location=event["currentIntent"]['slots']['location']
    print(location)
   
    

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
    slacktoken=secrets['slacktoken']
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
         
     
    print(eligiblefunctionalities) 
    # We will use the above to figure out if the member is authorized to do this work
    if not any("GuestVlan.help+Config Guest Vlan" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Config Port for guest Vlan. Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"int_port": portnum,"ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/252/launch/'
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
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for checking "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response


def port_uservlan(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['switch_name']
    print(devicename)
    portnum=event["currentIntent"]['slots']['port_num']
    print(portnum)
    location=event["currentIntent"]['slots']['location']
    print(location)
   

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
    slacktoken=secrets['slacktoken']
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
         
     
    print(eligiblefunctionalities)
    # We will use the above to figure out if the member is authorized to do this work
    if not any("UserVlan.help+Config User Vlan" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Config Port for User Vlan.  Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager 
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"int_port": portnum,"ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/256/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for checking "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response



def get_eligible_functionalities(userid,slacktoken):
    config = configparser.ConfigParser()
    config.read('ssbot.ini')
    authorisedset = set()  
    newset = set()
    thisdict = {}
    button_dict = {}
    try:
       for name  in config['ssbotpreferences']:
         if any(userid in s for s in getchannelmembers(name.upper(),slacktoken)): 
            string_value = config['ssbotpreferences'][name]
            x = string_value.split(",")
            for i in x:                               
              splitresults = i.split("-")
              if(splitresults[2] in thisdict):
                newset = thisdict[splitresults[2]]
                newset.add(splitresults[0]+"+"+splitresults[1])
                thisdict[splitresults[2]] = newset
              else:        
                thisdict[splitresults[2]]  = set([splitresults[0]+"+"+ splitresults[1]])

    except Exception as e:
      print(e)
      raise(e)  
    return thisdict



def reset_vedgeint(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['vedge_name']
    print(devicename)
    vedgeip=event["currentIntent"]['slots']['vedge_ip']
    print(vedgeip)
    #vpnid=event["currentIntent"]['slots']['vpn_id']
    #print(vpnid)
    interfacename=event["currentIntent"]['slots']['int_name']
    print(interfacename)
    location=event["currentIntent"]['slots']['location']
    print(location)
    
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
    slacktoken=secrets['slacktoken']
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
         
     
    print(eligiblefunctionalities) 
    # We will use the above to figure out if the member is authorized to do this work
    if not any("Reset.help+Vedge Reset Int" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to Reset Vedge Interface. Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"deviceIP": vedgeip,"ifname": interfacename,"ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/262/launch/'
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
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for checking "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response


def port_voicegw(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['switch_name']
    print(devicename)
    portnum=event["currentIntent"]['slots']['port_num']
    print(portnum)
    location=event["currentIntent"]['slots']['location']
    print(location)
   

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
    slacktoken=secrets['slacktoken']
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
    if not any("VoiceGwVlan.help+Config Voice GW" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Config Port for Voice GW.  Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager 
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"int_port": portnum,"ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/259/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job to configure Voice GW "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response

def reboot_vedge(event, context):
       
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
     
   
    # We will user the above intent name to differentiate what the customer is trying to do
    devicename=event["currentIntent"]['slots']['vedge_name']
    print(devicename)
    vedgeip=event["currentIntent"]['slots']['vedge_ip']
    print(vedgeip)
    chassis=event["currentIntent"]['slots']['chassis_num']
    print(chassis)
    location=event["currentIntent"]['slots']['location']
    print(location)
   

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
    slacktoken=secrets['slacktoken']
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
    if not any("RebootVedge.help+Vedge Reboot" in s for s in eligiblefunctionalities.values()):
       response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "User not authorized to do Config Port for Voice GW.  Contact Site Services."
                     },
                }
          }    
       return  response
 

    #Pull token from the SecretManager 
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
    tower_data = { "extra_vars": { "LOB": location,"cli": devicename,"deviceIP": vedgeip,"deviceId": chassis, "ss_requestor": emailid } }
    header={'Authorization': 'Bearer '+awxtoken, 'Content-Type': 'application/json'}
    url = 'https://awx.managed.karops.io/api/v2/workflow_job_templates/276/launch/'
    try:
      resp=sendhttprequest(tower_data,'POST',header,url)
    except Exception as e:
        response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Unable to submit Job to AWX Tower, please try again later"
                     },
                }
          }    
        print(e)  
        return response
    response_json=json.loads(resp.data.decode('utf-8'))
    print(response_json)
    
    
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
              "contentType":"SSML",
              "content": "Successfully Submitted Job for rebooting "+devicename+" in " + location + ". Please check channel: automation-alerts & your email for status."
            },
        }
    }


    return response

def show_help_response_card(event, context):
    print(event)
    userid_string=event['userId']
    userid = userid_string.split(':')[-1]
    #userid ='UDEBHDR9R'
    secrets=json.loads(get_secret())
    #Pull token from the SecretManager
    slacktoken=secrets['slacktoken']
    #print(slacktoken)
    #Lets first check if the user is eligible     
    #Checking whether the user is member of ssbot-fastgroup   
    authorised_dict = {}
     

     
    try:
      authorised_dict=get_eligible_functionalities(userid,slacktoken)
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

    finalresponse =[]
    button_dict_array =[]
    index=0
    print(authorised_dict)
    for keys in authorised_dict:
      button_dict_array = []
      for elements in authorised_dict[keys]:
        splitted = elements.split("+")
        button_dict = {"text": splitted[1], "value": splitted[0]}
        button_dict_array.append(button_dict)
      dict = {"title": keys, "subTitle": " ", "buttons":button_dict_array }
      finalresponse.append(dict)
    print(finalresponse)
    # check empty dictionary
    if not authorised_dict:
      button_dict_array={"title": "ssbot", "subTitle": "ssbot help" , "buttons": [{"text":"No Access. Contact Steve Humphrey","value":"help"}]} 
      finalresponse.append(button_dict_array)

      
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                 "contentType": "SSML",
                 "content": "Help"
                 },
            "responseCard": {
                "version": "2",
                "contentType": "application/vnd.amazonaws.card.generic",
                "genericAttachments": finalresponse
            }
        }

        }

    return response


def lambda_handler(event, context):
   
    intentname=event["currentIntent"]['name']
    print(intentname)

    if intentname == "ArubaCheckUpTime":
       return aruba_handler(event, context)
    elif intentname == "ArubaShowApUptime":
       return showAP_uptime(event, context)
    elif intentname == "RestartPrintSpooler":
       return restart_spooler(event, context)
    elif intentname == "AdesaGuestVlan":
       return port_guestvlan(event, context)
    elif intentname == "AdesaUserVlan":
       return port_uservlan(event, context)
    elif intentname == "ResetInterface":
       return reset_vedgeint(event, context)
    elif intentname == "RebootVedge":
       return reboot_vedge(event, context)	
    elif intentname == "VoiceGwVlan":
       return port_voicegw(event, context)
    elif intentname == "ssbotHelp":
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