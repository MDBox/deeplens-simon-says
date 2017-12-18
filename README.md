# Deeplens Simon-Says
<p>
An adventure into development on AWS Deeplens.  This repository outlines how we built a simon-says 
applicaiton using AWS deeplens to verify actions. The guinness world record for a game of Simon Says 
is 12,215 people set on June 14, 2007 at the Utah Summer Games.   
</p>

## Overview
<p>
The game platform can be broken down into two major catagories, AWS cloud services and Deeplens IoT devices services.
To start things off a cloudwatch event is triggered every minute that activates a lambda event to activate an athena query to find all possible game events.  
The results of the athena query is saved to an S3 bucket which then activates another lambda that generates a new Simon Says game.  This lambda will publich the 
results to an S3 bucket and to an SNS topic.  All devices that are subscribes to this topic will be notified of a new game.  The Deeplens devices will say the command
and the player will have 30~40 seconds to do the correct action.  A final message will be played if the player was successful or not.  
</p>

## Quick Setup

## Deeplens

## 