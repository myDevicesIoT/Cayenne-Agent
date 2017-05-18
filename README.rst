=============
Cayenne Agent
=============
The Cayenne Agent is a client for the `Cayenne IoT project builder <https://mydevices.com>`_. It will send system info as well as sensor and actuator info and respond to actuator messages initiated from the Cayenne dashboard and mobile apps.

************
Requirements
************
* `Python 3.x <https://www.python.org/downloads/>`_.
* pip3 - Python 3 package manager. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be::

 sudo apt-get install python3-pip

* python3-setuptools - Python 3 setuptools package. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be::

  sudo apt-get install python3-setuptools

* libiw-dev - Wireless tools development file package. Via `apt-get` this can be installed with::

  sudo apt-get install libiw-dev


***************
Getting Started
***************

Installation
============
This library can be installed by navigating to the root directory of the agent code and running the following command::

  sudo python3 setup.py install

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
