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
import scipy
import time
import numpy as np
import awscam
import cv2
import json
import requests
import shutil
import os
import mxnet as mx
from threading import Thread
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from scipy.ndimage.filters import gaussian_filter
from pygame import mixer

APISERVER = "https://8oci1836e9.execute-api.us-east-1.amazonaws.com"
APIKEY = "r92mIP3y8O47GZo4g3eMX8Z252rVjLkE8erOoB5D"

STATICFILES = "https://d1xdi6ekm1siot.cloudfront.net"

#Load Classification Model
feature_count = 15*2
category_count = 7
batch=10

X_pred = mx.nd.zeros((10,feature_count))
Y_pred = Y = mx.nd.empty((10,))

pred_iter = mx.io.NDArrayIter(data=X_pred,label=Y_pred, batch_size=batch)

filename = os.getcwd()+"/models/pose"
sym, arg_params, aux_params = mx.model.load_checkpoint(filename, 500)

new_model = mx.mod.Module(symbol=sym)
new_model.bind(pred_iter.provide_data, pred_iter.provide_label)
new_model.set_params(arg_params, aux_params)


class SimonGame:
    def __init__(self, deviceId):
        self.deviceId = deviceId
        self.gamerunning = False
        self.currentGame = None
        self.accesstimer = None
        self.gameMQTTClient = None
        self.requestRemoteAccess()

    def startGame(self, client, userdata, gamedata):
        if self.gamerunning:
		    return
        self.gamerunning = True
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
        self.gamerunning = False
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
    #try:
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
	game_count = 0
	poses = []
	collect_data = True
        while doInfer:
            # Get a frame from the video stream
            ret, frame = awscam.getLastFrame()
            
            # Raise an exception if failing to get a frame
            if ret == False:
                raise Exception("Failed to get frame from the stream")
            
            #Prepare Image for Network
            
            #print frame.shape
            center = frame.shape[1]/2
            left = center - (frame.shape[0]/2)
            scale = frame.shape[0]/184
            offset = (frame.shape[1] - frame.shape[0]) / 2
            
            cframe = frame[0:1520,left:left+1520,:]
            scaledImg = image_resize(cframe, width=184)
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
            #print (endt - startt)
            
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
            
            param={}
            param['octave'] = 3
            param['use_gpu'] = 1
            param['starting_range'] = 0.8
            param['ending_range'] = 2
            param['scale_search'] = [0.5, 1, 1.5, 2]
            param['thre1'] = 0.1
            param['thre2'] = 0.05
            param['thre3'] = 0.5
            param['mid_num'] = 4
            param['min_num'] = 10
            param['crop_ratio'] = 2.5
            param['bbox_ratio'] = 0.25
            param['GPUdeviceNumber'] = 3

            
            #print heatmap_avg.shape

            #plt.imshow(heatmap_avg[:,:,2])

            all_peaks = []
            peak_counter = 0

            for part in range(17-1):
                x_list = []
                y_list = []
                map_ori = heatmap_avg[:,:,part]
                map = gaussian_filter(map_ori, sigma=3)

                map_left = np.zeros(map.shape)
                map_left[1:,:] = map[:-1,:]
                map_right = np.zeros(map.shape)
                map_right[:-1,:] = map[1:,:]
                map_up = np.zeros(map.shape)
                map_up[:,1:] = map[:,:-1]
                map_down = np.zeros(map.shape)
                map_down[:,:-1] = map[:,1:]

                peaks_binary = np.logical_and.reduce((map>=map_left, map>=map_right, map>=map_up, map>=map_down, map > param['thre1']))
                peaks = zip(np.nonzero(peaks_binary)[1], np.nonzero(peaks_binary)[0]) # note reverse
                peaks_with_score = [x + (map_ori[x[1],x[0]],) for x in peaks]
                id = range(peak_counter, peak_counter + len(peaks))
                peaks_with_score_and_id = [peaks_with_score[i] + (id[i],) for i in range(len(id))]

                all_peaks.append(peaks_with_score_and_id)
                peak_counter += len(peaks)
            
            features = []
            noperson = False
            count = 0
            for f in all_peaks:
                if count == 15:
                    break
                count = count + 1
                if f == []:
                    noperson = True
                    break
                features.append([f[0][0],f[0][1]])
            
            if noperson:
                print "No Person Found in Image"
            else:
		game_count = game_count + 1
                pose = np.asarray(features)
                
                headsize = pose[1][1]-pose[0][1]*10
                shift = (pose[0][0],pose[0][1])
                for i in range(15):
                    pose[i][0] = pose[i][0] - shift[0]
                    pose[i][1] = pose[i][1] - shift[1]
                    
                
                pose = 1.0*pose/headsize
                
                #X_pred = mx.nd.empty((10,feature_count))
                #Y_pred = Y = mx.nd.empty((10,))
                
                #poses = [pose]
                
                pose = list(np.asarray(pose).reshape([15*2]))
                #print (poses[0])

		if collect_data == True:
			if game_count > 11:
				poses.append(pose)
			if game_count > 110:
				#doInfer =False
				game_count = 0
				print(list(poses))
				poses = []

		pose =np.asarray(pose)
		pose = mx.nd.array(pose)                
		X_pred[0] = pose

                #print(X_pred)
                pred_iter = mx.io.NDArrayIter(data=X_pred,label=Y_pred, batch_size=10)

                a = new_model.predict(pred_iter)[0]
                a= list(a.asnumpy())
                per = max(a)
		p = str(a.index(max(a)))
                print "pred: " + p
		mytext = "" 
                if p == "0":
			mytext = "No Pose"
		if p == "1":
			mytext = "Right Hand" 
		if p == "2":
			mytext = "Left Hand"
		if p == "4" or p == "5":
			mytext = "Touch Head"
		if p == "3":
			mytext = "Clap"
		if p == "6":
			mytext = "Raise Hands"
		color = (0,0,0)
		if per<0.5:
			color = (0,0,255)
		else:
			color = (255,0,0)

		cv2.putText(frame, mytext, (20,150), cv2.FONT_HERSHEY_SIMPLEX, 5, color, 3)

		cv2.putText(frame, str(int(per*100))+"%", (20,400), cv2.FONT_HERSHEY_SIMPLEX, 5,color, 3)
                for i in range(15):
                    cv2.circle(frame, (features[i][0]*scale+offset,features[i][1]*scale), 20, (0,0,255), thickness=-1)
            
            ret,jpeg = cv2.imencode('.jpg', frame)
#    except Exception as e:
#        msg = "Test failed: " + str(e)
#        print e
	#client.publish(topic=iotTopic, payload=msg)

    # Asynchronously schedule this function to be run again in 15 seconds
    #Timer(15, greengrass_infinite_infer_run).start()

# Execute the function above
greengrass_infinite_infer_run()

# This is a dummy handler and will not be invoked
# Instead the code above will be executed in an infinite loop for our example
def function_handler(event, context):
    return
