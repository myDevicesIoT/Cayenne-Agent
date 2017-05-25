=============
Cayenne Agent
=============
The Cayenne agent is a full featured client for the `Cayenne IoT project builder <https://mydevices.com>`_. It sends system information as well as sensor and actuator date and responds to actuator messages initiated from the Cayenne dashboard and mobile apps. The Cayenne agent currently supports Rasbian on the Raspberry Pi but it can be extended to support additional Linux flavors and other platforms.

************
Requirements
************
* `Python 3 <https://www.python.org/downloads/>`_.
* pip3 - Python 3 package manager. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be:
  ::

    sudo apt-get install python3-pip

* python3-dev -  Python 3 header files and static library package. Via `apt-get` this can be installed with:
  ::

    sudo apt-get install python3-dev

* python3-setuptools - Python 3 setuptools package. This should already be available in Python 3.4+ and above. If it isn't in can be installed using the system package manager. Via `apt-get` this would be:
  ::

    sudo apt-get install python3-setuptools

* libiw-dev - Wireless tools development file package. Via `apt-get` this can be installed with:
  ::

    sudo apt-get install libiw-dev

All of the above packages can be installed at once via `apt-get` by running:
::

  sudo apt-get install python3-pip python3-dev python3-setuptools libiw-dev

***************
Getting Started
***************

Installation
============
The agent can be installed by navigating to the root directory of the agent code and running::

  sudo python3 setup.py install

Launching the Agent
===================
After install the agent can be launched by running the myDevices module from python::

  python3 -m myDevices

If you have not installed the Raspberry Pi on the device before you will be prompted to enter an invite code when the agent is first run. You can get the invite code from the Cayenne dashboard with the following steps.

1. Create an account at https://cayenne.mydevices.com, if you do not already have one.
2. Select **Add New...->Device/Widget->Single Board Computer->Raspberry Pi**.
3. Under **Option 2** you will see some Linux commands. You do not need to run these commands. Instead you can get the invite code from the script name: rpi_[invitecode].sh.
4. Enter that invite code at the agent prompt and press Enter.
5. The agent will run and connect to Cayenne and your device will show up in the device list.
   
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
        
   d) Optionally, disable the Cayenne service from starting at boot.
      ::
       
        sudo systemctl disable myDevices
  
3. Run this agent module in place of the Cayenne agent service, instead of from the command line.
   ::
   
     sudo service myDevices start

Other potential issues caused by running this agent along side the Cayenne service:

* File/folder permissions issues - The permissions for files and folders used by this agent, including ``/var/log/myDevices``, ``/etc/myDevices``, ``/var/run/myDevices`` and files inside those folders, could conflict with the permissions set by the agent service installed from Cayenne. To get around this issue you can manually modify the file and folder permissions, reinstall the agent, or run the agent as a service as explained above.
* Agent update - The Cayenne agent will automatically update itself if a new agent becomes available which can overwrite the installation of this agent. You may need to reinstall this agent if that happens. To completely disable updates you can add the line ``DoUpdates = false`` to ``/etc/myDevices/AppSettings.ini``.

***********
Development
***********
The agent can be installed for doing development in place by navigating to the root directory of the agent code and running::

  sudo python3 setup.py develop

When running the agent logs information to stderr as well as ``/var/log/myDevices/cayenne.log``. To enable additional debug logging use the ``-d`` option on the command line:
::
  
  python3 -m myDevices -d

Currently the agent has code for interfacing with several sensors and actuators and support for the Raspberry Pi. If you would like to extend that you can add support for additional sensors, actuators and boards as described below.
  
Supporting Additional Sensors/Actuators
=======================================
To add support for additional sensors/actuators you may need to create new modules for the specific sensors/actuators.

Creating a new sensor/actuator module
-------------------------------------

* Create a new module for the sensor/actuator under the appropriate ``myDevices.devices`` subfolder. For instance, a new analog device should be added under ``myDevices.devices.analog``.
* Add a class for your sensor/actuator inside the new module.
* Derive the class from appropriate bus type and sensor/device types, if applicable. For example, the BMP085 class in the ``myDevices.devices.sensors.bmp085`` is an I²C temperature and pressure sensor so it is derived from ``myDevices.devices.i2c.I2C``,  ``myDevices.devices.sensor.Temperature``, and ``myDevices.devices.sensor.Pressure``.
* Override the read/write functions of the parent class that your device needs to support with sensor specific functionality. For example a digital sensor would need to override the ``__digitalRead__`` function. An analog actuator would need to override the ``__analogWrite__`` function.
* Add the device module and class to the ``DRIVERS`` dict in the appropriate ``myDevices.devices`` subfolder ``__init__.py`` file. For an analog device that would mean adding it to the ``DRIVERS`` dict in ``myDevices.devices.analog.__init__.py``. The dict key is the name of the module, the value is a list of classes within the module.

Testing that the new sensor/actuator module works
-------------------------------------------------
To verify that the sensor/actuator works correctly you can test it with the following functions.

* Create a new sensor using ``myDevices.sensors.SensorsClient.AddSensor`` using the appropriate device name and any args required by your device.
* Get the sensor values using ``myDevices.sensors.SensorsClient.SensorsInfo`` and make sure the sensor data is correct.
* If the new device is an actuator set the actuator value using ``myDevices.sensors.SensorsClient.SensorCommand``.
* Delete the sensor using ``myDevices.sensors.SensorsClient.DeleteSensor``.

An example demonstrating these functions is available in ``myDevices.test.client_test.py``.

*Note:* For security reasons the Cayenne agent is designed to be able to run from an account without root privileges. If any of your sensor/actuator code requires root access consider running just that portion of your code via a separate process that can be launched using sudo. For example, the ``myDevices.devices.digital.ds2408`` module uses this method to write data.

Supporting Additional Boards
============================
To add support for additional boards beyond the Raspberry Pi you may need to modify I/O, system info and/or settings modules as required for the board.

Pin and Bus I/O
---------------
Current support for pin and bus I/O is based on the Linux filesystem drivers used on the Raspberry Pi. To support a different board you may need to update the agent code for the following items, depending on what functionality the board has:

Native GPIO Pins
  Native GPIO pin support is provided in ``myDevices.devices.digital.gpio.py``. This uses the Linux file system drivers under ``/sys/class/gpio`` for reading and writing to GPIO pins. It also uses the ``/dev/gpiomem`` memory map to determine pin modes. If your board is a Linux based board that supports the same filesystem drivers at the same location you may be able to use this code as-is. Otherwise you may need to modify the filesystem driver location or replace the drivers with a some other method or library for reading and writing GPIO values. If your board doesn't support the ``/dev/gpiomem`` memory mapped file you may be able to get the same pin mode info from ``/dev/mem`` or perhaps another GPIO library. Or just fallback to using the filesystem drivers and only get basic pin modes.

SPI Bus
  SPI bus support is provided in ``myDevices.devices.spi.py``. This uses the Linux file system drivers under ``/dev/spidev0.*``. If your board is a Linux based board that supports the same filesystem drivers at the same location you may be able to use this code as-is. Otherwise you may need to modify the filesystem driver location or replace the drivers with a some other method or library for reading and writing SPI values.

I²C Bus
  I²C bus support is provided in ``myDevices.devices.i2c.py``. This uses the Linux file system drivers under ``/dev/i2c-*``. If your board is a Linux based board that supports the same filesystem drivers at the same location you may be able to use this code as-is. Otherwise you may need to modify the filesystem driver location or replace the drivers with a some other method or library for reading and writing I²C values.

1-Wire Bus
  1-Wire bus support is provided in ``myDevices.devices.onewire.py``. This uses the Linux file system drivers under ``/sys/bus/w1/devices``. If your board is a Linux based board that supports the same filesystem drivers at the same location you may be able to use this code as-is. Otherwise you may need to modify the filesystem driver location or replace the drivers with a some other method or library for reading and writing 1-Wire values.

Serial Bus
  Serial bus support is provided in ``myDevices.devices.serial.py`` This uses the Linux file system drivers under ``/dev/ttyAMA0``. Currently Cayenne doesn't support any sensors or actuators using the serial bus so you probably don't need to support this, unless you add some sensor or actuator that requires it.

Loading/Unloading Bus Kernel Modules
  Support for loading/unloading bus kernel modules is provided in ``myDevices.devices.bus.py``. This uses the Linux program ``modprobe``. If your board uses the same bus kernel modules and supports ``modprobe`` you may be able to use this code as-is. Otherwise you may need to update the modules listed in ``BUSLIST`` and/or modify the code to load the kernel modules. If you don't need to support loading the bus kernel modules you can stub out this code.

System info
-----------
Information about the device, including CPU, RAM, etc., is currently retrieved via several modules including a C library compiled for the Raspberry Pi, though that will be changed to a Python only implementation in the future. To support a different board you may need to update the agent code for the following items, if applicable:

General System Info
  General system info, including CPU, RAM, memory, etc. is retrieved via ``myDevices.os.systeminfo.py`` This is mostly implemented via a C library for the Raspberry Pi, though that will be changed to a Python only implementation in the future. If the C library doesn't work on your device you can disable the C library call until the Python implementation is available at which point you can modify it to support your board.

Hardware Info
  Hardware info, including make, model, etc. is retrieved via ``myDevices.cloud.vcom_id.py``. This should be modified or overridden to provide the appropriate hardware info for your board.

Pin Mapping
  The mapping of the on-board pins is provided in ``myDevices.utils.version.py`` with the ``MAPPING`` list. This list provides the available GPIO pin numbers as well as the voltage ("V33", "V50"), ground ("GND") and do-not-connect ("DNC") pins. This should be updated with the mapping for your board. However, the Cayenne dashboard is currently built to display the Raspberry Pi GPIO layout so if your board's pin layout is significantly different it may not display correctly in the GPIO tab.

Settings
--------
Currently the Raspberry Pi agent has settings for enabling/disabling the device tree, SPI, I²C, serial and camera. These are set via the ``myDevices.os.raspiconfig`` module which runs a separate Bash script at ``/etc/myDevices/scripts/config.sh``. If any of these settings are available on your board and you would like to support them you can override or replace ``myDevices.os.raspiconfig.py``. Otherwise the settings functionality can be ignored.

*Note:* For security reasons the Cayenne agent is designed to be able to run from an account without root privileges. If any of your I/O, system info or settings code requires root access consider running it via a separate process that can be launched using sudo. For example, the ``myDevices.os.raspiconfig`` module uses this method to update config settings.

************
Contributing
************
The Cayenne agent is an open source project and welcomes your contributions, including:

* Bug reports and fixes
* Documentation improvements
* Additional sensor/actuator support
* Additional board support
* Other code enhancements

*****************
Cayenne Community
*****************
Join us on Slack at `slack.mydevices.com <http://slack.mydevices.com/>`_ or in the `Cayenne Community <http://community.mydevices.com>`_.

*******
License
*******
`MIT <LICENSE>`_
