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
here will be organized in the same way.
Each package has a list of the hardware involved in this package, a list of automations with a 
short description on what the automation does and some additional description for the package.

## Lovelace
-- Under Construction --

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

**Hue Dimmer Switch next to the bed** [sleep.py](https://github.com/Burningstone91/smart-home/blob/master/appdaemon/configuration/apps/sleep.py)

The Hue Dimmer Switch executes the following actions depending on the button pressed:
* Short press ON button: Turn off all lights and devices in the house and start a
                         good night playlist in the bedroom
* Short press UP button: Increase brightness by 10%
* Long press UP button: Increase volume 
* Short press DOWN button: Decrease brightness by 10%
* Short press OFF button: Turn lights off
* Long press OFF button: Turn dehumidifier off

