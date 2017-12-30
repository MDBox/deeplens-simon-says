from threading import Timer, Thread
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from pygame import mixer
import time
import json
import requests
import shutil
import os

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
        self.currentGame = json.loads(gamedata.payload)
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
        except:
            print("Audio not working")
        

        
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

Write_To_FIFO = True
class FIFO_Thread(Thread):
    def __init__(self):
        ''' Constructor. '''
        Thread.__init__(self)
        
    def run(self):
        while Write_To_FIFO:
            time.sleep(10)

results_thread = FIFO_Thread()
results_thread.start()

game = SimonGame('test')
