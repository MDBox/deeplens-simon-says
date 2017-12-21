const AWS = require("aws-sdk");
const iot = new AWS.Iot();
const sts = new AWS.STS();
const roleName = 'simonsays-notifications';

exports.handler = (event, context, callback) => {

    const params = {};
    let deviceId = '';
    
    if (event.queryStringParameters !== null && event.queryStringParameters !== undefined) {
        if (event.queryStringParameters.deviceId !== undefined && 
            event.queryStringParameters.deviceId !== null && 
            event.queryStringParameters.deviceId !== "") {
            console.log("Received deviceId: " + event.queryStringParameters.deviceId);
            deviceId = event.queryStringParameters.deviceId;
        }else{
            return callback('missing deviceId', {statusCode: 400});
        }
    }

    iot.describeEndpoint({}).promise().then(data => {
      params.iotEndpoint = data.endpointAddress;
      params.region = 'us-east-1';
      return sts.getCallerIdentity({}).promise();
    }).then(data => {
        return sts.assumeRole({
            RoleArn: `arn:aws:iam::${data.Account}:role/${roleName}`,
            RoleSessionName: deviceId
        });
    }).then(data => {
        params.accessKey = data.Credentials.AccessKeyId;
        params.secretKey = data.Credentials.SecretAccessKey;
        params.sessionToken = data.Credentials.SessionToken;
        callback(null, {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify(params)
        });
    }).catch(err => {
        callback(err, {
            statusCode: 500,
            body: err.message
        });
    });
};