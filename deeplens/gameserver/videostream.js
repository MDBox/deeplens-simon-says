const spawn = require('child_process').spawn;

const command = 'ffmpeg';

const videostream = function(){
    this.arguments = '-i /opt/awscam/out/ch1_out.h264 -c:v h264 -flags +cgop -g 30 -hls_time 1 out.m3u8'.split(' ');
};

videostream.prototype.Start = function(){
    this.running = true;
    let ffmpeg = this.ffmpeg = spawn(command, this.arguments);
    
    ffmpeg.on('close', (exitcode) => {
        console.log(`child process exited with code ${exitcode}`);
        if(this.running){
            setTimeout(function(){
                this.Start();
            }, 5000, this);            
        }
    });
    
    ffmpeg.stderr.on('data', (data) => {
        console.error(`stderr: ${data}`);
    });
    
    ffmpeg.stdout.on('data', (data) => {
        console.log(`stdout: ${data}`);
    });
    
    return ffmpeg;
};


videostream.prototype.Stop = function(){
    this.running = false;
    this.ffmpeg.kill();
};

module.exports = videostream;