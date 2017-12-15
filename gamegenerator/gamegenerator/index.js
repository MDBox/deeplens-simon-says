const AWS = require("aws-sdk");

exports.handler = (event, context, callback) => {
    const athena = new AWS.Athena();
    const queryId = event.Records[0].s3.object.key.split('.')[0];

    console.log(queryId);
    
    var params = {
      QueryExecutionId: queryId, /* required */
      MaxResults: 100
    };

    athena.getQueryResults(params, function(err, data) {
        if (err) console.log(err, err.stack); // an error occurred
        else{
            console.log(data.ResultSet);           // successful response
            console.log(data.ResultSetMetadata.ColumnInfo);
            const max = data.ResultSet.Rows.length;
            const randomEvent = Math.floor(Math.random() * (max - 0 + 1));
            console.log(data.ResultSet.Rows[randomEvent]);
          
        }
    });
    
    
    callback();
};