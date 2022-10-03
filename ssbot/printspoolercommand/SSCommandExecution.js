var AWS = require('aws-sdk');
const kms = new AWS.KMS({ region: 'us-east-1' })

const authchannel_name = "GQREQMKDW"
var Request = require("request");

var token, kmsEncyptedToken, slackToken, towerToken, slackToken2;




kmsEncyptedToken = "AQICAHicWiwnCYtQ5usefnrXGyN605ZteQOC+HAJTsvLOq6KiAEZXophO5Uvm6LurxfzOjx2AAAAdzB1BgkqhkiG9w0BBwagaDBmAgEAMGEGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQMCB7DYrFpj0vi1PBiAgEQgDRU8+WB0N88Tn9Af9r5KplyMR3F/ypABgxRnrtug7K0WriF6e8wQFLyHPOxeomotHzlJ6Jg"
slackToken = "AQICAHicWiwnCYtQ5usefnrXGyN605ZteQOC+HAJTsvLOq6KiAHY09sd/UlIRkAbtMlluX9HAAAAmjCBlwYJKoZIhvcNAQcGoIGJMIGGAgEAMIGABgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDAijcnVbOO7wrP4JvQIBEIBTK3hiG9+DmAjmDULr6b7T9EXLovf0wP+5MBnRh5NzbWJtGFmregPTlbONWjB/OP5zhOlhLoz3Eoedm9OS+HoaIkOqAqI73icIm+qJ2qawvvveZc0="
towerToken = "AQICAHicWiwnCYtQ5usefnrXGyN605ZteQOC+HAJTsvLOq6KiAFcR9ymJ9S1JEtx4KXsxB9/AAAAfTB7BgkqhkiG9w0BBwagbjBsAgEAMGcGCSqGSIb3DQEHATAeBglghkgBZQMEAS4wEQQM6+ufQM3b6vZfYhOWAgEQgDrPFopsx1R9TLX4yegqKTUDvsfRTZjHoTpZ+7Gklk9BWU0PPdzs87I3lVd1fu8fLOpbSCZFDJ2SLbgv"
slackToken2 = "AQICAHicWiwnCYtQ5usefnrXGyN605ZteQOC+HAJTsvLOq6KiAERlGiYKuMgTYqnKevnRoOcAAAArzCBrAYJKoZIhvcNAQcGoIGeMIGbAgEAMIGVBgkqhkiG9w0BBwEwHgYJYIZIAWUDBAEuMBEEDFo8RmSSIWsYbqoEdwIBEIBoOsB6/zaPYZtFrVdDsyv3ML0Lz3nBjZBg3ICTzoCF67EwKkkp8M1gkVM0nIjIvvufITi75tH+nFqzp5vK5O8Y4K3F7KskNskkdPQ2HyVMhGcBuk0P2P0m515eqbrUTCUoN2NFyjou888="


var decrypedTowerToken, decryptedSlackToken, decryptedKMSToken, decryptedslacktoken, decryptedtowertoken, decryptedslacktoken2, decryptedSlackToken2;



exports.handler = async function(event, context, callback) {

    var user_id = event.user_id;
    var command = event.command;
    var channel = event.channel_name;
    var commandText = event.text;
    var JobDetails, jobid;


    var decryptedkmstoken = await DecryptToken(kmsEncyptedToken).then(function(result) {
        // console.log('decryped token' + result);
        token = result;
    });

    var decryptedslacktoken = await DecryptToken(slackToken).then(function(result) {
        // console.log('decryped slacktoken' + result);
        decryptedSlackToken = result;
    });

    var decryptedslacktoken2 = await DecryptToken(slackToken2).then(function(result) {
        console.log('decryped slacktoken' + result);
        decryptedSlackToken2 = result;
    });


    var decryptedtowertoken = await DecryptToken(towerToken).then(function(result) {
        // console.log(' decryptedtowertoken' + result);
        decrypedTowerToken = result;
    });


    var istokenvalid = await checktoken(event, context, callback).then(function(result) {
        // console.log('Valid token' + result);
    });

console.log(decryptedSlackToken2.trim());

    var channeldetails = await GetSlackGroupmembers("GQREQMKDW", decryptedSlackToken2.trim()).then(function(result) {
        // console.log('Groupmember list' + result);
        var slackgroupdetails = result;

        if (slackgroupdetails.ok) {
            //  console.log("Members " + slackgroupdetails.group.members);
            if (slackgroupdetails.group.members.indexOf(user_id) != -1) {
                // console.log("User found ");


            }
            else {
                console.log("User not found");
                callback(null, 'No Access');
            }
        }
        else {
            console.log("Channel not found");
            callback(null, 'Channel not found');
        }


    });

console.log(decrypedTowerToken.trim());

    var submitTowerJob = await submitJob(285, commandText, decrypedTowerToken.trim()).then(function(result) {
        //console.log("Got the Job  Id");

        JobDetails = result;
        jobid = JobDetails.id;
        // console.log("Got the Job  Id" + jobid);
    });


console.log(decryptedSlackToken.trim());

    var postslackmessage = await PostMessagetoSlack(event.channel_id, event.user_name + " restarted " + commandText + " Successfully", decryptedSlackToken.trim()).then(function(result) {
        //console.log("Got the Job  Id");

        var SlackPostStatus = result;

        //console.log("Slack PostMessage" + SlackPostStatus);
    });




    callback(null, 'Success');






};


async function PostMessagetoSlack(channelname, message, slacktoken) {

    return new Promise(function(resolve, reject) {

        var jsonDataObj = { 'channel': channelname, 'text': message };
        Request.post({
            url: 'https://slack.com/api/chat.postMessage',
            json: true,
            body: jsonDataObj,
            headers: {
                'Authorization': 'Bearer ' + slacktoken
            },
            rejectUnauthorized: false
        }, function(err, res) {
            if (err) {
                console.error(err);
            }
            else {
                // console.log(res.body);
                resolve(res.body);
            }


        });

    })
}


async function checktoken(event, context, callback) {

    var requestToken = event.token;
    return new Promise(function(resolve, reject) {

        //console.log(token);

        if (requestToken.trim() !== token.trim()) {
            console.error("Request token (" + requestToken + ") does not match expected");
            // callback(1,"Sorry Invalid Token")
            resolve(1);

        }
        else {

            // console.log("Token validated");
            resolve(0);
            //  callback(0, 'Success');


        }
    });


}

async function submitJob(jobid, servername, towertoken) {

    return new Promise(function(resolve, reject) {





        var jsonDataObj = { 'limit': servername };



        Request.post({
            url: 'https://tower.karops.io/api/v2/job_templates/' + jobid + "/launch/",
            json: true,
            body: jsonDataObj,

            headers: {
                'Authorization': 'Bearer ' + towertoken
            },
            rejectUnauthorized: false
        }, function(err, res) {
            if (err) {
                console.error(err);
            }
            else {
                // console.log(res)
                resolve(res.body);
            }


        });
    })
}





async function GetSlackGroupmembers(channel_name, slacktoken2) {

    return new Promise(function(resolve, reject) {
        Request({
            url: 'https://slack.com/api/groups.info?channel=' + channel_name,
            headers: {
                'Authorization': 'Bearer ' + slacktoken2
            },
            rejectUnauthorized: false
        }, function(err, res) {
            if (err) {
                console.error(err);
                resolve("error");
            }
            else {
                //  console.log(res.body);
                resolve(JSON.parse(res.body));
            }


        });

    })
}


async function DecryptToken(kmsEncyptedToken) {
    var decryptedtoken;
    return new Promise(function(resolve, reject) {
        var encryptedBuf = Buffer.from(kmsEncyptedToken, 'base64');
        var cipherText = { CiphertextBlob: encryptedBuf };
        // console.log("Inside DecryptToken");

        kms.decrypt(cipherText, function(err, data) {
            if (err) {
                console.log(err, err.stack)
            }
            else {

                var decryptedScret = data['Plaintext'];

                decryptedtoken = decryptedScret.toString();
                // console.log(decryptedtoken);
                resolve(decryptedtoken);
            }
        })





    })
}

