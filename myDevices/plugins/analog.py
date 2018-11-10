"""
This module provides classes for interfacing with analog plugins.
"""
import json
from myDevices.plugins.manager import PluginManager
from myDevices.utils.logger import info


class AnalogInput():
    """Reads data from an analog input."""

    def __init__(self, adc_name):
        """Initializes the analog input.
        
        Arguments:
            adc_name: Name of analog-to-digital converter plugin in the format 'plugin_name:section'
        """
        self.adc_name = adc_name
        self.adc = None
        self.read_args = {}
        self.pluginManager = PluginManager()
        self.set_adc()
    
    def set_adc(self):
        """Sets the ADC plugin."""
        if not self.adc:
            self.adc = self.pluginManager.get_plugin_by_id(self.adc_name)
            self.read_args = json.loads(self.adc['read_args'])

    def read_value(self, channel, data_type=None):
        """Read the data value on the specified channel."""
        self.set_adc()
        value = getattr(self.adc['instance'], self.adc['read'])(channel, data_type=data_type, **self.read_args)
        return value
       
    def read_float(self, channel):
        """Read the float value on the specified channel."""
        return self.read_value(channel, 'float')
    
    def read_volt(self, channel):
        """Read the voltage on the specified channel."""
        return self.read_value(channel, 'volt')
