# Deeplens Simon-Says
This project is an entry into #AWSDeepLensChallenge.

## Overview
Simon Says is a childhood game where the players act out the commands from "Simon". When Simon "say" to do something you do the action, however when Simon doesn't give the command you should not do the action. Our project is building a Simon Says Deep Learning platform where everyone can join the same global game using Deeplens to verify the correct action of each player.

<b>Fun Fact:</b> The guinness world record for a game of Simon Says is 12,215 people set on June 14, 2007 at the Utah Summer Games.

<img src="media/body_pose.png">Pose Map</img>

## Application
<img src="media/network_overview.png" width="60%"></img>
### Define Goals
- Have the device issue a `simon says` command.
- Monitor the camera stream and classify the players action.
- Overlay a display of the player's pose and current action.
- Link the device to a global simon game network.  


The game platform can be broken down into two major catagories, AWS cloud services and Deeplens IoT devices.
To start things off a cloudwatch event is triggered every minute that activates an Athena query to find all possible game events.  
The results of the Athena query is saved to an S3 bucket which then generates and publish a new Simon Says game to S3 and SNS.
All devices that are subscribes to the SNS topic will be notified of a new game.  The Deeplens devices will say the command, generated from AWS Polly,
and the player will have 30~40 seconds to do the correct action.  A final message will be played if the player was successful or not.  With this design
all players around the world will be able to play the same game of Simon Says at the same time.  

### Stage 2
A local server can be started from the Deeplens devices that will broadcast the two camera input streams to the local network.  This will allow other devices such as
smart phones to access and use the devices without needing a monitor/TV.  The deeplens devices will also submit game results along with a thumbnail to an S3 bucket. Players will be able to
see the results from everyone who participated in the game via web interface.

### Stage 3
For the final stage of development the Simon Says game will ask the players to perform a random action which will be used to expan the game events. The deeplens will
ask the user to describe the action and it will be package the response and video which will be processed using sagemaker.  Sagemaker will use this video and classification
to expand the game.  

## Quick Setup

## Deeplens

##
