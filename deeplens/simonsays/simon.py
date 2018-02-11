#
# Copyright Amazon AWS DeepLens, 2017
#

# greengrassInfiniteInfer.py
# Runs GPU model inference on a video stream infinitely, and
# publishes a message to topic 'infinite/infer' periodically.
# The script is launched within a Greengrass core.
# If function aborts, it will restart after 15 seconds.
# Since the function is long-lived, it will run forever 
# when deployed to a Greengrass core. The handler will NOT 
# be invoked in our example since we are executing an infinite loop.

import os
#import greengrasssdk
from threading import Timer
import time
import numpy as np
import awscam
import cv2
import json
import requests
import shutil
import os
from threading import Thread
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from pygame import mixer

APISERVER = "https://8oci1836e9.execute-api.us-east-1.amazonaws.com"
APIKEY = "r92mIP3y8O47GZo4g3eMX8Z252rVjLkE8erOoB5D"

STATICFILES = "https://d1xdi6ekm1siot.cloudfront.net"

class SimonGame:
    def __init__(self, deviceId):
        self.deviceId = deviceId
        self.currentGame = None
        self.accesstimer = None
        self.gameMQTTClient = None
        self.requestRemoteAccess()

    def startGame(self, client, userdata, gamedata):
        print("start game")
        #print(gamedata.payload.decode("utf-8"))
        self.currentGame = json.loads(gamedata.payload.decode("utf-8"))
        print(self.currentGame)
        self.gametimer = Timer(45, self.submitGameResults)
        self.gametimer.start()
        self.playSound()

    def downloadSoundClip(self, key):
        print("download sound clip")
        r = requests.get(STATICFILES+"/music/"+key, stream=True)
        if r.status_code == 200:
            with open("/tmp/"+key, "wb") as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                
    def playSound(self):
        soundclip = self.currentGame["name"]
        if self.currentGame["simonsays"]:
            soundclip += "_simon.mp3"
        else:
            soundclip += ".mp3"

        if not os.path.isfile('/tmp/'+soundclip):
            print("Need to download file: " + soundclip)
            self.downloadSoundClip(soundclip)

        try:
            mixer.init()
            mixer.music.load('/tmp/'+soundclip)
            mixer.music.play()
        except Exception as e:
            msg = "Test failed: " + str(e)
            print msg
            
    def submitGameResults(self):
        if self.gametimer is not None:
            self.gametimer.cancel()
        print("Submit Game Results")
        
    # Join the global MQTT Simon Game Service
    def requestRemoteAccess(self):
        if self.accesstimer is not None:
            self.accesstimer.cancel()

        if self.gameMQTTClient is not None:
            self.gameMQTTClient.disconnect()

        print("Request Access")
        req = requests.get(APISERVER+'/prod/activate', {"deviceId": self.deviceId}, headers={"x-api-key": APIKEY})
        cred = req.json()

        self.gameMQTTClient = AWSIoTMQTTClient(self.deviceId,
            useWebsocket=True)
        self.gameMQTTClient.configureCredentials("./caroot.pem")
        self.gameMQTTClient.configureEndpoint(cred['iotEndpoint'], 443)
        self.gameMQTTClient.configureIAMCredentials(cred["accessKey"], cred["secretKey"], cred["sessionToken"])
        if self.gameMQTTClient.connect():
            print("connected to global MQTT service")
        if self.gameMQTTClient.subscribe("simongame", 0, self.startGame):
            print("subscribed to simon game channel")

        self.accesstimer = Timer(60*45, self.requestRemoteAccess)

    def getCurrentGame(self):
        return self.currentGame;

# Creating a greengrass core sdk client
#client = greengrasssdk.client('iot-data')
#iotTopic = '$aws/things/{}/infer'.format(os.environ['AWS_IOT_THING_NAME'])

ret, frame = awscam.getLastFrame()
ret,jpeg = cv2.imencode('.jpg', frame) 
Write_To_FIFO = True
class FIFO_Thread(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
 
    def run(self):
        fifo_path = "/tmp/results.mjpeg"
        if not os.path.exists(fifo_path):
            os.mkfifo(fifo_path)
        f = open(fifo_path,'w')
        #client.publish(topic=iotTopic, payload="Opened Pipe")
        while Write_To_FIFO:
            try:
                f.write(jpeg.tobytes())
            except IOError as e:
                continue  

                
### Helper Functions ##
def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation = inter)

    # return the resized image
    return resized

def padRightDownCorner(img, stride, padValue):
    h = img.shape[0]
    w = img.shape[1]

    pad = 4 * [None]
    pad[0] = 0 # up
    pad[1] = 0 # left
    pad[2] = 0 if (h==184) else 184-h # down
    pad[3] = 0 if (w==184) else 184-w # right

    img_padded = img
    pad_up = np.tile(img_padded[0:1,:,:]*0 + padValue, (pad[0], 1, 1))
    img_padded = np.concatenate((pad_up, img_padded), axis=0)
    pad_left = np.tile(img_padded[:,0:1,:]*0 + padValue, (1, pad[1], 1))
    img_padded = np.concatenate((pad_left, img_padded), axis=1)
    pad_down = np.tile(img_padded[-2:-1,:,:]*0 + padValue, (pad[2], 1, 1))
    img_padded = np.concatenate((img_padded, pad_down), axis=0)
    pad_right = np.tile(img_padded[:,-2:-1,:]*0 + padValue, (1, pad[3], 1))
    img_padded = np.concatenate((img_padded, pad_right), axis=1)

    return img_padded, pad

## Greengrass Loop ##
def greengrass_infinite_infer_run():
    try:
        game = SimonGame('test')
        ##TODO FIX THIS PATH
        modelPath = "/home/aws_cam/faster_184.xml"

        # Send a starting message to IoT console
        #client.publish(topic=iotTopic, payload="Simon Say Game Starting")
        results_thread = FIFO_Thread()
        results_thread.start()

        # Load model to GPU (use {"GPU": 0} for CPU)
        mcfg = {"GPU": 1}
        model = awscam.Model(modelPath, mcfg)
        #client.publish(topic=iotTopic, payload="Model loaded")

        doInfer = True
        while doInfer:
            # Get a frame from the video stream
            ret, frame = awscam.getLastFrame()
            
            # Raise an exception if failing to get a frame
            if ret == False:
                raise Exception("Failed to get frame from the stream")
            
            #Prepare Image for Network
            frame = frame[0:1520,0:1520,:]
            scaledImg = image_resize(frame, width=184)
            heatmap_avg = np.zeros((scaledImg.shape[0], scaledImg.shape[1], 16))
            paf_avg = np.zeros((scaledImg.shape[0], scaledImg.shape[1], 28))

            imageToTest = cv2.resize(scaledImg, (0,0), fx=1, fy=1, interpolation=cv2.INTER_CUBIC)
            #print imageToTest.shape
            imageToTest_padded, pad = padRightDownCorner(imageToTest, 8, 128)

            #print pad
            transposeImage = np.transpose(np.float32(imageToTest_padded[:,:,:]), (2,0,1))/255.0-0.5


            startt = time.time()
            output = model.doInference(transposeImage)
            endt = time.time()
            print (endt - startt)
            
            h = output["Mconv7_stage4_L2"]
            p = output["Mconv7_stage4_L1"]
            #print len(h)
            heatmap1 = h.reshape([16,23,23]) 
            heatmap = np.transpose(heatmap1, (1,2,0))

            #print heatmap1.shape
            #print heatmap.shape
            #heatmap = np.moveaxis(h, 0, -1)

            heatmap = cv2.resize(heatmap, (0,0), fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
            heatmap = heatmap[:imageToTest_padded.shape[0]-pad[2], :imageToTest_padded.shape[1]-pad[3], :]
            heatmap = cv2.resize(heatmap, (scaledImg.shape[1], scaledImg.shape[0]), interpolation=cv2.INTER_CUBIC)
            #print(heatmap)
            heatmap_avg = heatmap_avg + heatmap / 1

            paf1 = p.reshape([28,23,23])
            paf = np.transpose(paf1, (1,2,0))

            #paf = np.moveaxis(result[0].asnumpy()[0], 0, -1)
            paf = cv2.resize(paf, (0,0), fx=8, fy=8, interpolation=cv2.INTER_CUBIC)
            paf = paf[:imageToTest_padded.shape[0]-pad[2], :imageToTest_padded.shape[1]-pad[3], :]
            paf = cv2.resize(paf, (scaledImg.shape[1], scaledImg.shape[0]), interpolation=cv2.INTER_CUBIC)
            #print paf.shape

            paf_avg = paf_avg + paf / 1
            #print inferOutput
            #print output
            msg = "{"
            probNum = 0 
            font = cv2.FONT_HERSHEY_SIMPLEX
            #cv2.putText(frame, outMap[topFive[0]["label"]], (0,22), font, 1, (255, 165, 20), 4)
            #for obj in topFive:
            #    if probNum == 4: 
            #        msg += '"{}": {:.2f}'.format(outMap[obj["label"]], obj["prob"])
            #    else:
            #        msg += '"{}": {:.2f},'.format(outMap[obj["label"]], obj["prob"])
            #    probNum += 1
            #msg += "}"
            #print msg
            #client.publish(topic=iotTopic, payload=msg)
            global jpeg
            #print heatmap.shape
            #print heatmap_avg.shape
            #print scaledImg.shape
            dst = scaledImg
            dst[:,:,2] = dst[:,:,2]+ (heatmap_avg[:,:,15]+0.5)/2*255
            
                
            #dst = blend_transparent(scaledImg[:,:,2], heatmap_avg[:,:,15])
            #dst = cv2.addWeighted(scaledImg, 0.3, heatmap_avg[:,:,15][:,:,0], 0.7, 0)
            ret,jpeg = cv2.imencode('.jpg', dst)
    except Exception as e:
        msg = "Test failed: " + str(e)
        print msg
	#client.publish(topic=iotTopic, payload=msg)

    # Asynchronously schedule this function to be run again in 15 seconds
    #Timer(15, greengrass_infinite_infer_run).start()

# Execute the function above
greengrass_infinite_infer_run()

# This is a dummy handler and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    return
