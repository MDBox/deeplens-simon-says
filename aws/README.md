## AWS Backend

### Event Generator
The event generator is used to query S3 using Athena for a current list of possible game actions.  
The current system only has 5 actions but with this approach, we can extend the game by uploading
a new game file to S3 and it will be introduced in the next round.  

```javascript 1.6
const AWS = require("aws-sdk");

exports.handler = (event, context, callback) => {
    const athena = new AWS.Athena();
    
    const query = 'SELECT * FROM "simon"."deeplens_simon" WHERE active = true;'
    
    var params = {
        QueryString: query,
        ResultConfiguration: {
            OutputLocation: 's3://{bucket-name}',
        },
    };
    athena.startQueryExecution(params).promise().then(data =>{
        console.log(data);
        callback(null, data);
    }).catch(err => {
        console.log(err, err.stack);
        callback(err);
    })
};
```

### Game Generator
The game generator lambda is used to read the results from Athena.  It will pick at random the next game state and choose if `simon says` or not.
After the game is generated it is saved to S3 and also published to IoT channel.

```javascript 1.6
const AWS = require("aws-sdk");

exports.handler = (event, context, callback) => {
    const athena = new AWS.Athena();
    const s3 = new AWS.S3();
    const sns = new AWS.SNS();
    const iotdata = new AWS.IotData({endpoint: '{IoT Endpoint}'});
    const queryId = event.Records[0].s3.object.key.split('.')[0];

    console.log(queryId);

    var params = {
      QueryExecutionId: queryId, /* required */
      MaxResults: 100
    };

    athena.getQueryResults(params).promise().then(data => {
        const max = data.ResultSet.Rows.length - 1;
        const randomEvent = Math.floor(Math.random() * max) + 1;
        const gameevent = data.ResultSet.Rows[randomEvent];
        
        let simonsays = true;
        if((Math.random()*10) > 5){
            simonsays = false;
        }

        const gamestate = {
            action: gameevent.Data[1].VarCharValue,
            name: gameevent.Data[0].VarCharValue,
            simonsays: simonsays,
            startdate: (new Date()).toString(),
            gameid: queryId,
        };
        
        return s3.putObject({
            Body: JSON.stringify(gamestate),
            Bucket: '{S3 bucket to Save Game objects}',
            Key: 'games/'+ queryId + '/game.json'
        }).promise().then(data => {
            // console.log('wrote to s3');
            const params = {
              topic: 'simongame', /* required */
              payload: JSON.stringify(gamestate) /* Strings will be Base-64 encoded on your behalf */,
              qos: 0
            };
            return iotdata.publish(params).promise();
        });
    }).then(data => {
        console.log('publish to SNS topic');
        callback();  
```


### Game Subscriber
The game subscriber is a lambda that is used by API Gateway.  It is responsible for granting access to the IoT channel.  
When the deeplens devices is started it will make an API request to gain temporary credentials to access the game network.  We generate these 
temporary credentials using AWS STS and Assume Role, giving our credentials limited access.  

```javascript 1.6
const AWS = require("aws-sdk");
const iot = new AWS.Iot();
const sts = new AWS.STS();
const roleName = 'simonsays-notifications';

exports.handler = (event, context, callback) => {

    const params = {};
    let deviceId = '';
    
    console.log(event)
    
    if (event.queryStringParameters !== null && event.queryStringParameters !== undefined) {
        if (event.queryStringParameters.deviceId !== undefined && 
            event.queryStringParameters.deviceId !== null && 
            event.queryStringParameters.deviceId !== "") {
            console.log("Received deviceId: " + event.queryStringParameters.deviceId);
            deviceId = event.queryStringParameters.deviceId;
        }
    }
    
    if(deviceId === ''){
        return callback('no deviceId', {
            statusCode: 400
        });
    }

    iot.describeEndpoint({}).promise().then(data => {
      params.iotEndpoint = data.endpointAddress;
      params.region = 'us-east-1';
      return sts.getCallerIdentity({}).promise();
    }).then(data => {
        console.log(data.Account)
        return sts.assumeRole({
            RoleArn: `arn:aws:iam::${data.Account}:role/${roleName}`,
            RoleSessionName: deviceId
        }).promise();
    }).then(data => {
        console.log(data);
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
``` 

`simonsays-notifications` Policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iot:Receive",
                "iot:Subscribe",
                "iot:Connect"
            ],
            "Resource": "*"
        }
    ]
}
```
`simonsays-notifications` Trust Relation
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::????:role/cloud9-gamesubscriber-gamesubscriberRole-?????"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```