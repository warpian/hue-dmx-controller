Copyright (c) 2023 Tom Kalmijn / MIT License.

# hue-dmx-controller
### author: Tom Kalmijn

## What this script does
With this script you can integrate DMX fixtures with the Philips Hue bridge and Hue mobile app.

## Rationale
I wrote this script because I wanted to install some special lighting in my living room. I could not find fixtures
in a variant where one can simply replace the bulb with a Philips Hue compatible bulb. 

## DMX Controller
In order to integrate DMX in your Hue system you need a DMX controller. I choose to use the ENTTEC DMX USB dongle
which is cheap and reliable. If you like to use a different DMX controller with this script then the script 
needs to be adapted to communicate with that controller.

## Fixtures
I currently have two DMX fixtures: an American DJ Saber Spot WW and an American DJ Saber Spot RGBW. The script
has two classes to communicate with them: Dmx4ChRgbw and Dmx1ChDimmable. These classes have generic names because
there must be lots of other fixtures that have the same channel dmx configurations. If you like to use a fixture
with a different channel configuration then you need to write a new class derived from DmxFixture and override
a single method: ```get_dmx_message(...)```. This method converts incoming Hue information into a DMX message.

Currently supported fixture profiles:

| name           | num channels | byte | purpose | range |
|----------------|--------------|------|---------|-------|
| Dmx1ChDimmable | 1            | 1    | dimming | 0-255 |
| Dmx4ChRgbw     | 4            | 1    | red     | 0-255 |
|                |              | 2    | green   | 0-255 |
|                |              | 3    | blue    | 0-255 |
|                |              | 4    | white   | 0-255 |

### Note: ENTTEC OPEN DMX PRO is not supported

## How it works
This script connects to your Hue bridge using the new Hue Clip API v2. This new API has a facility to 
listen for events rather than using polling to see if a light has changed (on/off/brightness/color). When
you turn on a light using the Hue app an event will come in and the script will see if there is a DMX
fixture registered for the event. If so it will ask a specialised DmxFixture class to convert Hue light
information into a DMX message. Finally the script will send that message onto the DMX wire.

## DMX Hold
This script does not repeat the DMX channels (like e.g. 44 times per seconds), instead it only sends a 
DMX message when a light changes. This means that your fixture must support a 'Hold' function that will
prevent the fixture from blacking out. 

## Script configuration
Adapt the included .env file (with example values) to configure the script. Here you specify the IP
address of your Hue bridge, the Hue API key, etc.
```
WORK_DIR=.
PID=/var/run/hue-dmx.pid
LOG_FILE=./hue-dmx.log
HUE_BRIDGE_IP=192.168.0.140
HUE_API_KEY=wazMEHP-1elntYnEbc6on6j8CI7H3GqZSSVrBp6V
DAEMONIZE=false
STUB_DMX=false

FIXTURE1_NAME=Bureau
FIXTURE1_DMX_ADDRESS=2
FIXTURE1_HUE_ID=e0a5dd4a-67d3-4f40-ab6d-67c8ebbd463d
FIXTURE1_CLASS=Dmx4ChRgbw

FIXTURE2_NAME=Buddha
FIXTURE2_DMX_ADDRESS=1
FIXTURE2_HUE_ID=74b88e35-f81e-4f5a-b7af-3730ae5de366
FIXTURE2_CLASS=Dmx1ChDimmable

# FIXTURE3_NAME=... etc
```

## Hue compatible bulb
Because the Hue API does not let us create a virtual light bulb we will have to use an actual (cheap) Hue
compatible bulb. First connect the bulb to the bridge as usual, then just take the bulb offline (put it
in a drawer). The bulb will show up in Hue app as 'unreachable' but this can be ignored. Turning on/off 
the light will work just fine. The bulb should have the features your DMX fixture require. So if your DMX
fixture supports setting its color, the Hue compatible bulb should alo support that.

## Adaptations and new features
Please do not hesitate to contact me for bug fixes or feature requests.




