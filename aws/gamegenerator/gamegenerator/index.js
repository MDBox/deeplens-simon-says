const AWS = require("aws-sdk");

exports.handler = (event, context, callback) => {
    const athena = new AWS.Athena();
    const s3 = new AWS.S3();
    const sns = new AWS.SNS();
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
        
        gamestate.default = JSON.stringify(gamestate);
        
        console.log(gamestate);
        
        return s3.putObject({
            Body: JSON.stringify(gamestate),
            Bucket: 'deeplens-simonsays',
            Key: 'games/'+ queryId + '/game.json'
        }).promise().then(data => {
            console.log('wrote to s3');
            const params = {
                Message: JSON.stringify(gamestate),
                MessageStructure: 'json',
                TopicArn: 'arn:aws:sns:us-east-1:378707175638:simsonsays'
            };
            return sns.publish(params).promise();
        });
    }).then(data => {
        console.log('publish to SNS topic');
        callback();  
    }).catch(err => {
        console.log(err, err.stack);
        callback(err);
    });
};