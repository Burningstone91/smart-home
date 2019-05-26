# Burningstone Smart Home

## Introduction

I use an Intel NUC i3 with Proxmox running different VMs and one of them is the Smart Home.
A ConBee ZigBee Stick and an Aeotec Z-Wave Stick are attached to the NUC to control all
the ZigBee and Z-Wave devices.
A Docker Host inside an Ubuntu Server VM builds the core of the Smart Home.

### Docker Host Services: 

* AppDaemon - For Automations
* Deconz - To control ZigBee devices through the ConBee Stick
* Glances - To monitor the system status of the host
* Grafana - To visualize sensor data of the house
* Ha-Dockermon - To monitor and control the docker containers
* Home Assistant - Tying it all together
* InfluxDB - Database for the data from home-assistant
* LetsEncrypt - To access my home from outside with an SSL-encrypted connection
* Mosquitto - MQTT Server

All my automations are done with AppDaemon.
My Home-Assistant and AppDaemon Configuration are organized with packages and my documentation 
here will be organized in the same way. Each package has a list of the hardware involved in 
this package and a list of automations with a short description on what the automation does. 
But first I will start with an explanation of the AppDaemon Core Apps and the setup. 

## Lovelace
I only recently started using lovelace so my setup is a huge work in progress. Below is a screenshot of some of my panels.

### Automation Controls
![Alt text](/hass/configuration/lovelace_screenshots/automation_controls.png?raw=true "Automation Controls")
Input booleans to turn on/off automations.

### System Monitor
![Alt text](/hass/configuration/lovelace_screenshots/system_monitor.png?raw=true "System Monitor")
System monitor shows: 
* Status of my NAS 
* Status of Docker host
* Statistics about the network speed and ping
* Switches to enable/disable docker services
* Version installed and available for AppDaemon and Home Assistant
* Battery Level of Smart Home devices

### Floorplan
![Alt text](/hass/configuration/lovelace_screenshots/floorplan.png?raw=true "Floorplan")
Floorplan of the house. Features:
* Shows open state of doors/windows, doors leading to outside show up red when opened
* Control light
* Turn on/off speakers, membrane icon beating when music is playing
* Turn on/off dehumifier, fan icon spinning when dehumidifier is on
* Turn on/off projector
* Turn on/off vacuum robot




## AppDaemon Core Apps
### AppBase [appbase.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/appbase.py)
This is the base for all AppDaemon apps. Each app uses this module as a base and therefore
all the variables and methods can be used by the app. 

Each app can be configured to be disabled based on conditions.
* Presence: App disabled when someone, noone, everyone is home
* Modes: App disabled when specified mode is in specified state, e.g. don't run if guest mode is 'on'
* Days: App disabled on specified days
* Input boolean: App disabled when the input boolean of the app is off

The AppBase creates a reference to every dependency specified in the configuration. 

The AppBase creates a holding place for entities, handles, notifications ans properties.

The AppBase uses voluptuous to check the configuration files for bad input or syntax.

### Notifications [notification.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/notification.py)
This is the base for all notifications. A notification has a level 'home' or 'emergency'
and a type 'single' or 'repeat'.

An 'emergency' message will always be sent no matter if the person is home or asleep.

A 'home' message will be sent if the target is home and awake, otherwise the message
will be added to the briefing list. Each item in the briefing list will be sent to the target
when it arrives home or when the sleep mode is deactivated.

A 'single' message will be sent once.

A 'repeat' message will be sent so long until it gets cancelled.

### Presence [presence.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/presence.py)
This is the base for presence detection. I use Pi Zero W distributed around the house to detect bluetooth Nut mini which
are attached to our keys. This app sets the presence input boolean for each person when the state of the Nut mini changes.

The setup is configured to differentiate between 'just arrived', 'home', 'just left', 'away' and 'extended away'.

The presence app also sets the presence input boolean of the house based on the input boolean of the different persons.
The state of the house can be 'everyone home', 'no one home', 'vacation', 'someone home'.

### Switches [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)
This is the base for all kind of switches. The different kind of Switches are:
* Toggle on state change: toggles a switch or calls a service when the specified entity enters the specified state
* Toggle at time: toggles a switch or calls a service at the specified time
* Toggle on arrival: toggles a switch or calls a service when someone or a specified person arrives at home
* Toggle on departure: toggles a switch or calls a service when everyone left the house
* Hue Dimmer Switch: toggles a switch or calls a service based on the specified button presses in the config




## Bedroom
### Configuration files
* Home-Assistant config: [bedroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/bedroom.yaml)
* AppDaemon config: [bedroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/bedroom.yaml)

### Hardware used
* 3x Hue Bulb Color for the ceiling
* 1x Hue Bulb Color for a small background light
* 1x Hue Dimmer Switch next to the Bed
* 1x Hue Dimmer Switch next to the light switch
* 1x Denon Heos 5 HS2 Speaker
* 1x myStrom Switch for the dehumidifier
* 1x "Smart" dehumidifier which turns itself on/off if humidity is above/below set threshold
* 1x Aqara Door/Window Sensor for the window
* 1x Aqara Door/Window Sensor for the door
* 1x USB-powered Aeotec Z-Wave Multisensor for motion, temperature and humidity

### Automations
**Motion based lightning** [motion_light.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/motion_light.py)

When motion is detected, the light turns on based on time of the day and turns off after a specified
delay.

**Hue Dimmer Switch next to light switch** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn light on 100% brightness
* Short press UP button: Increase brightness by 10%
* Short press DOWN button: Decrease brightness by 10%
* Short press OFF button: Turn lights off
* Long press OFF button: Turn dehumidifier off

**Hue Dimmer Switch next to the bed** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn off all lights and devices in the house and start a
                         good night playlist in the bedroom
* Short press UP button: Increase brightness by 10%
* Long press UP button: Increase volume by 5%
* Short press DOWN button: Decrease brightness by 10%
* Long press DOWN button: Decrease volume by 5%
* Short press OFF button: Stop music in bedroom and turn off all lights and devices in the house
* Long press OFF button: Start a timer to stop music in 15 minutes

**Dehumidifier** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The dehumidifier is turned on when everyone left the house. In the future the dehumidifier should be
turned on/off based on a bayesian "in bed" sensor, which I'm currently testing. This sensor determines
whether I'm in bed based on state of different entities, time of day etc. 

**Turn on/off dehumidifier when window closes/opens** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

Turns off the dehumidifier when the bedroom window is opened. Turns it on when it closes, but only if it the sleep mode is not activated

## Climate
### Configuration files
* Home-Assistant config: [climate.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/climate.yaml)
* AppDaemon config: [climate.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/climate.yaml)

### Hardware used
* 4x Aeotec Z-Wave Multisensor for temperature and humidity in bedroom, small bathroom, office and dressroom
* 8x Aqara Door/Window sensor for all windows/doors leading out of the house

### Automations
**Notification on high humidity** [climate.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/climate.py)

Sends a notification on a specified interval with a list of all rooms with humidity above the defined threshold.

**Notification on open window** [climate.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/climate.py)

Sends a notification when a door/window leading to the outside is left open longer than the specified threshold.

## Dressroom
### Configuration files
* Home-Assistant config: [dressroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/dressroom.yaml)
* AppDaemon config: [dressroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/dressroom.yaml)

### Hardware used
* 3x Hue Bulb Color for the ceiling
* 1x Hue Dimmer Switch next to the light switch
* 1x Aqara Door/Window Sensor for the window
* 1x Aqara Door/Window Sensor for the door
* 1x USB-powered Aeotec Z-Wave Multisensor for motion, temperature and humidity

### Automations
**Motion based lightning** [motion_light.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/motion_light.py)

When motion is detected, the light turns on based on time of the day and turns off after a specified
delay.

**Hue Dimmer Switch next to light switch** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn light on 100% brightness
* Short press UP button: Increase brightness by 10%
* Short press DOWN button: Decrease brightness by 10%
* Short press OFF button: Turn lights off

## House
### Configuration files
* Home-Assistant config: [house.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/house.yaml)
* AppDaemon config: [house.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/house.yaml)

### Hardware used
* 1x Aqara Door/Window Sensor for the house door

### Automations
**Everyone left** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

Starts the scene "Alle weg", which:
* Turns off all lights
* Switches on the dehumidifier
* Starts the Power Off action in the Harmony remote
* Turns of the Stereo Receiver in the office

## Kitchen
### Configuration files
* Home-Assistant config: [kitchen.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/kitchen.yaml)
* AppDaemon config: [kitchen.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/kitchen.yaml)

### Hardware used
* 1x Hue Bulb Color for the lamp above the dining table
* 1x myStrom Switch for the dishwasher
* 1x Aqara Door/Window Sensor for the window to the garden
* 1x Aqara Door/Window Sensor for the door to the balcony

### Automations
**IN PROGRESS - Notify on dishwaser done** [washer.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/washer.py)

Sends an actionable notification when the dishwasher completed a cycle and sets the dishwasher to clean. 
When someone presses "Erledigt" in response to the notification, the dishwasher is set to dirty.

## Livingroom
### Configuration files
* Home-Assistant config: [livingroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/livingroom.yaml)
* AppDaemon config: [livingroom.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/livingroom.yaml)

### Hardware used
* 2x Hue Bulb Color for a lamp in the back and the front
* 1x Hue Dimmer Switch
* 1x Aqara Door/Window Sensor for the window
* 1x Aqara Door/Window Sensor for the door to the balcony
* 1x Harmony Remote
* 1x Denon AVR X2300W
* 1x Epson TW-6300W Projector
* 1x Nintendo Switch
* 1x Minix X8H-Plus Kodi player
* 1x Cable TV-Box

### Automations
**Scene based lightning** [home_cinema.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/home_cinema.py)

Turns the light on based on the currently active scene on the harmony remote.

**Hue Dimmer Switch** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn light on 100% brightness
* Short press UP button: Increase brightness by 10%
* Short press DOWN button: Decrease brightness by 10%
* Short press OFF button: Turn lights off

**Pause on phone call** [home_cinema.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/home_cinema.py)

Pauses the current activity of the harmony remote and turns the light on when 
someone is having a phone call, return to previous state when phone call ends. 
The phone call is detected with tasker and tasker turns an input boolean on/off 
depending on the state of the call.

**Brighten light on pause** [home_cinema.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/home_cinema.py)

Increases the brightness when the current activity on the harmony is paused and returns
to the previous state if the activity is resumed. Using emulated Roku to send button presses
from the Harmony Remote to Home Assistant. 

## Office
### Configuration files
* Home-Assistant config: [office.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/office.yaml)
* AppDaemon config: [office.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/office.yaml)

### Hardware used
* 3x Hue Bulb White for the ceiling
* 1x Hue Dimmer Switch next to the light switch
* 1x Aqara Door/Window Sensor for the window
* 1x Aqara Door/Window Sensor for the door
* 1x USB-powered Aeotec Z-Wave Multisensor for motion, temperature and humidity
* 2x PC as device tracker with the ping component
* 1x Yamaha RN-602D Stereo receiver

### Automations
**Motion based lightning** [motion_light.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/motion_light.py)

When motion is detected, the light turns on based on time of the day and turns off after a specified
delay. If one of the computers or the Yamaha receiver is running, motion will not trigger an
action.

**Hue Dimmer Switch next to light switch** [switches.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/switches.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn light on 100% brightness
* Short press UP button: Increase brightness by 10%
* Short press DOWN button: Decrease brightness by 10%
* Short press OFF button: Turn lights off
* Long press OFF button: Turn Yamaha receiver off

## Reminders
### Configuration files
* AppDaemon config: [reminders.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/reminders.yaml)

### Automations
Possible frequency types are 'days', 'weeks', 'months'. 
E.g. frequency type 'days' and frequency '3' --> sends a reminder every third day after the specified date.

**Remind new battery key Dimitri** [reminder.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/reminder.py)

Sends a reminder every 5 months to change the battery of the nut mini.

**Remind new battery key Sabrina** [reminder.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/reminder.py)

Sends a reminder every 5 months to change the battery of the nut mini.


## Security
### Configuration files
* Home-Assistant config: [security.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/security.yaml)
* AppDaemon config: [security.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.yaml)

### Hardware used
* 4x Aeotec Z-Wave Multisensor for motion in bedroom, small bathroom, office and dressroom
* 15x Aqara Door/Window sensor for all windows/doors being opened
* 12x Hue light bulbs for flashing lights on alert

### Automations
**Arm when everyone gone** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Arms the security system when everyone left the house.

**Disarm when someone arrives** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Disarm the security system when someone arrives at home.

**Disarm when cleaning** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Disarm the motion sensors when the vacuum robot is cleaning to avoid false alerts.

**Notify on alarm change** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Send a notification when the state of the security system changed.

**Notify on bad login attempt** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Send a notification containing the ip of the user when a bad login attempt to home assistant was made.

**Update last motion sensor** [security.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/security.py)

Updates the 'last motion' sensor with the name of the room in which the last motion was detected.

## System Monitor
### Configuration files
* Home-Assistant config: [systems.yaml](https://github.com/Burningstone91/smart-home/blob/master/hass/configuration/config/packages/systems.yaml)
* AppDaemon config: [system_monitor.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.yaml)

### Hardware used

### Automations
**Notify on device going offline** [system_monitor.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.py)

Send a notification when one of the specified devices goes offline. Offline state is determined 
with ping or with status 'unavailable' or 'unknown'.

**Notify on AppDaemon Error** [system_monitor.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.py)

Send a notification when there is an error in the AppDaemon log.

**Notify on low battery** [system_monitor.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.py)

Send a notification when the battery of one of the specified batteries is below the specified
threshold.

**Update Appdaemon installed version sensor** [system_monitor.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.py)

Updates the 'appdaemon version' sensor with the latest installed versioin of appdaemon every 24 hours.

**Notify on new version** [system_monitor.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/system_monitor.py)

Send a notification when there is a new version available for AppDaemon or HomeAssistant.

## Vacuum
### Configuration files
* AppDaemon config: [vacuum.yaml](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/vacuum.yamll)

### Hardware used
* 1x Roomba 960 vacuum robot

### Automations
**Run scheduled cleaning cycle** [vacuum.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/vacuum.py)

Starts the vacuum robot on specified day and time to clean the house. When someon arrives at home, 
the vacuum robot returns to the base. 

**Notify on device going offline** [vacuum.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/vacuum.py)

Send a notification when the bin of the vacuum is full. 
