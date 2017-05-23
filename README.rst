=============
Cayenne Agent
=============
The Cayenne agent is a full featured client for the `Cayenne IoT project builder <https://mydevices.com>`_. It sends system information as well as sensor and actuator date and responds to actuator messages initiated from the Cayenne dashboard and mobile apps. The Cayenne agent currently supports Raspberry Pi.

************
Requirements
************
* `Python 3 <https://www.python.org/downloads/>`_.
* pip3 - Python 3 package manager. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be:
  ::

    sudo apt-get install python3-pip
 
* python3-setuptools - Python 3 setuptools package. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be:
  ::

    sudo apt-get install python3-setuptools

* libiw-dev - Wireless tools development file package. Via `apt-get` this can be installed with:
  ::

    sudo apt-get install libiw-dev


***************
Getting Started
***************

Installation
============
This library can be installed by navigating to the root directory of the agent code and running::

  sudo python3 setup.py install

Launching the Agent
===================
After install the agent can be launched by running the myDevices module from python::

  python3 -m myDevices

If you have not installed the Raspberry Pi on the device before you will be prompted to enter an invite code when the agent is first run. You can get the invite code from the Cayenne dashboard with the following steps.

1. Create an account at https://cayenne.mydevices.com, if you do not already have one.
2. Select **Add New...->Device/Widget->Single Board Computer->Raspberry Pi**.
3. Under **Option 2** you will see some Linux commands. You don not need to run these commands. Instead you can get the invite code from the script name: rpi_[invitecode].sh.
4. Enter that invite code at the agent prompt and press Enter.
5. The agent will run and connect to Cayenne and you device will show up in the device list.
   
Potential conflicts with the Cayenne service
--------------------------------------------
If you have already have installed the Cayenne agent service via the Cayenne dashboard you might see some conflicts if you also try running this agent manually. To get around this you can do one of the following:

1. Uninstall the Cayenne agent service.
   ::

     sudo /etc/myDevices/uninstall/uninstall.sh
  
2. Shut down the Cayenne agent service.

   a) Open crontab for editing.
      ::
        
        sudo crontab -e
      
   b) Comment out or remove the myDevices cron job to prevent the service from automatically restarting, then save and exit.
   c) Stop the Cayenne service.
      ::
      
        sudo service myDevices stop
  
3. Run this agent module in place of the Cayenne agent service, instead of from the command line.
   ::
   
     sudo service myDevices start

Other potential issues caused by running this agent along side the Cayenne service:

* File/folder permissions issues - The permissions for files and folders used by this agent, including `/var/log/myDevice`, `/etc/myDevices`, `/var/run/myDevices` and files inside those folders, could conflict with the permissions set by the agent service installed from Cayenne. To get around this issue you can manually modify the file and folder permissions, reinstall the agent, or run the agent as a service as explained above.
* Agent update - The Cayenne agent will automatically update itself if a new agent becomes available which can overwrite the installation of this agent. You may need to reinstall this agent if that happens.

***************************************
Supporting Additional Sensors/Actuators
***************************************
To add support for additional sensors/actuators you may need to create new modules for the specific sensors/actuators.

Creating a new sensor/actuator module
=====================================

* Create the new module under the appropriate `myDevices.devices` subfolder, e.g. new analog devices should be added under `myDevices.devices.analog`.
* Derive the device's class from appropriate bus type, e.g. `myDevices.devices.i2c.I2C`, and sensor type, e.g. `myDevices.devices.sensor.Temperature`, if applicable.
* Override the read/write functions of the parent class, `__digitalRead__`, `__analogWrite__`, etc., with sensor specific read/write functionality.
* Add the device module/class to the `DRIVERS` in the `myDevices.devices` subfolder `__init__.py` file.

Testing that the new sensor/actuator module works
=================================================

* Create a new sensor using `myDevices.sensors.SensorsClient.AddSensor`.
* Get the sensor values using `myDevices.sensors.SensorsClient.SensorsInfo` and make sure the sensor's data is returned.
* If the new device is an actuator set the actuator value using `myDevices.sensors.SensorsClient.SensorCommand`.
* Delete the sensor using `myDevices.sensors.SensorsClient.DeleteSensor`.

.. note:: For security reasons the Cayenne agent is designed to be able to run from an account without root privileges. If any of your sensor/actuator code requires root access consider running it via a separate process that can be launched using sudo.

****************************
Supporting Additional Boards
****************************
To add support for additional boards you may need to modify I/O, bus and settings modules as required for the board.

I/O modules
===========
Current support for pin and bus I/O is based on the filesystem drivers used on the Raspberry Pi. To support a different board you may need to update the following modules, depending on what functionality the board has:

* `myDevices.devices.digital.gpio.py` - Native GPIO pin support
* `myDevices.devices.spi.py` - SPI bus support
* `myDevices.devices.i2c.py` - I²C bus support
* `myDevices.devices.onewire.py` - 1-Wire bus support
* `myDevices.devices.serial.py` - Serial bus support
* `myDevices.devices.bus.py` - Generic bus class, as well as code for loading/unloading bus kernel modules

System info
===========
Information about the device, including CPU, RAM, etc., is currently retrieved via several modules including a C library compiled for the Rasberry Pi, though that may be changed to a Python only implementation in the future. To support a different board you may need to update the following modules, if applicable:

* `myDevices.os.systeminfo.py` - Retrieves general system info, including CPU, RAM, memory, etc. This is mostly implemented via a C library for the Raspberry Pi, though that may be changed to a Python only implementation in the future.
* `myDevices.cloud.vcom_id.py` - Retrieves device make, model, etc.
* `myDevices.utils.version.py` - Information about the board pin mapping

Settings
========
Currently the Raspberry Pi agent has settings for enabling/disabling the device tree, SPI, I²C, serial and camera. These are set via the `myDevices.os.raspiconfig.py` module. If any of these settings are available on your board and you would like to support them you can override or replace that file. Otherwise the settings functionality can be ignored.

.. note:: For security reasons the Cayenne agent is designed to be able to run from an account without root privileges. If any of your I/O, system or settings code requires root access consider running it via a separate process that can be launched using sudo.
