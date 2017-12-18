const AWS = require("aws-sdk");

exports.handler = (event, context, callback) => {
    const athena = new AWS.Athena();
    
    const query = 'SELECT * FROM "simon"."deeplens_simon" WHERE active = true;'
    
    var params = {
        QueryString: query,
        ResultConfiguration: {
            OutputLocation: 's3://aws-athena-query-results-378707175638-us-east-1',
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