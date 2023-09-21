MIT License

Copyright (c) 2023 Tom Kalmijn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

# hue-dmx-controller
### author: Tom Kalmijn

## What this script does
With this script you can integrate DMX fixtures with the Philips Hue bridge and Hue mobile app.

## Rationale
I wrote this script because I wanted to install some special lighting in my living room. I could not find fixtures
in a variant where one can simply replace the bulb with a Philips Hue compatible bulb. 

## DMX Controller
In order to integrate DMX in your Hue system you need a DMX controller. I choose to use the ENTTEC DMX USB dongle
which is cheap and reliable. If you like to use a different DMX controller with this script than the script 
needs to be adapted to communicate with that controller.

## Fixtures
I currently have two DMX fixtures: an American DJ Saber Spot WW and an American DJ Saber Spot RGBW. If you 
like to use other fixtures with this script you need derive from the class DmxFixture class. Your derived
class overrides one method 'def get_dmx_message' that converts incoming Hue information into a DMX message
which is specific for your fixture.

#### Note: ENTTEC OPEN DMX PRO is not supported (please contact me via github for feature requests)

## How it works
This script connects to your Hue bridge using the new Hue Clip API v2. This new API has a facility to 
listen for events rather than using polling to see if a light has changed (on/off/brightness/color). When
you turn on a light using the Hue app an event will come in and the script will see if there is a DMX
fixtured registered for the event. If so it will ask your specialised DmxFixture derived class to convert
information about the light into a DMX message. Then the script will send that message onto the DMX wire.

## DMX Hold
This script does not repeat the DMX channels (like e.g. 44 times per seconds), instead it only sends a 
DMX message when a light changes. This means that your fixture must support a 'Hold' function that will
prevent the fixture from black out. 

## Usage
Adapt the included .env file (with example values) to configure the script. In .env you specify the IP
address of your Hue bridge, the Hue API key, etc. 

## Adaptations and new features
Please do not hesitate to cContact me for bug fixes or feature requests.




