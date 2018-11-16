"""
This module provides classes for interfacing with analog and PWM plugins.
"""
from myDevices.plugins.io import InputOutput
from myDevices.utils.logger import info, debug


class AnalogInput(InputOutput):
    """Reads data from an analog or PWM plugin input."""

    def __init__(self, plugin_id):
        """Initializes the plugin input.
        
        Arguments:
            plugin_id: Plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
        """        
        InputOutput.__init__(self, plugin_id, 'analog', 'in')
       
    def read_float(self, channel):
        """Read the float value on the specified channel."""
        return self.read_value(channel, 'float')
    
    def read_volt(self, channel):
        """Read the voltage on the specified channel."""
        return self.read_value(channel, 'volt')
    
    def read_angle(self, channel):
        """Read the angle on the specified channel."""
        return self.read_value(channel, 'angle')


class AnalogIO(AnalogInput):
    """Reads/writes data from an analog or PWM plugin input/output."""

    def __init__(self, plugin_id, function):
        """Initializes the plugin input/output.
        
        Arguments:
            plugin_id: Plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
            function: The pin function, 'in' if the pin is an input, 'out' if it is an output 
        """        
        InputOutput.__init__(self, plugin_id, 'analog', function)
       
    def write_float(self, value, channel):
        """Write the float value on the specified channel."""
        return self.write_value(value, channel, 'float')

    def write_volt(self, value, channel):
        """Write the voltage on the specified channel."""
        return self.write_value(value, channel, 'volt')

    def write_angle(self, value, channel):
        """Write the angle on the specified channel."""
        return self.write_value(value, channel, 'angle')


class AnalogOutput(AnalogIO):
    """Reads/writes data from an analog or PWM plugin input/output."""

    def __init__(self, plugin_id):
        """Initializes the plugin input/output.
        
        Arguments:
            plugin_id: Plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
        """        
        AnalogIO.__init__(self, plugin_id, 'out')
  