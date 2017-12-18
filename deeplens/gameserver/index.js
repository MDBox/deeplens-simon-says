const AWS = require("aws-sdk");
const express = require("express");
const videostream = require("./videostream")();
const app = express();

videostream.Start();


app.get('/', (req, res) => {
    
});

app.get('/stream', (req, res) => {
    
});

app.get('/stream/raw', (req, res) => {
    
});

app.get('/stream/processed', (req, res) => {
    
});


app.listen('8888');