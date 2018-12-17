"""
This module provides classes for interfacing with digital plugins.
"""
from myDevices.plugins.io import InputOutput
from myDevices.utils.logger import info, debug, exception


class DigitalInput(InputOutput):
    """Reads data from an digital input."""

    def __init__(self, plugin_id):
        """Initializes the plugin input.
        
        Arguments:
            plugin_id: Plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
        """        
        InputOutput.__init__(self, plugin_id, 'in', 'digital_sensor')

    def value_to_tuple(self, value):
        """Converts value to tuple with the appropriate Cayenne data type."""
        try:
            return (int(value), self.data_type)
        except:
            return InputOutput.value_to_tuple(self, value)


class DigitalOutput(DigitalInput):
    """Reads and writes data from a digital output."""

    def __init__(self, plugin_id):
        """Initializes the digital input/output.
        
        Arguments:
            plugin_id: Plugin ID in the format 'plugin_name:section', e.g. 'cayenne-mcp23xxx:MCP'
        """
        InputOutput.__init__(self, plugin_id, 'out', 'digital_actuator')