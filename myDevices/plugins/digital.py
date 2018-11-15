"""
This module provides classes for interfacing with digital plugins.
"""
from myDevices.plugins.manager import PluginManager
from myDevices.utils.logger import info, debug, exception


class DigitalIO():
    """Reads data from an digital input/output."""

    def __init__(self, gpio, function):
        """Initializes the digital input/output.
        
        Arguments:
            gpio: The GPIO plugin ID in the format 'plugin_name:section', e.g. 'cayenne-mcp23xxx:MCP'
            function: The pin function, 'in' if the pin is an input, 'out' if it is an output
        """
        self.gpio_name = gpio
        self.gpio = None
        self.function = function.lower()
        self.current_functions = {}
        self.read_args = {}
        self.write_args = {}
        self.plugin_manager = PluginManager()
        self.set_gpio()
    
    def set_gpio(self):
        """Sets the GPIO plugin."""
        if not self.gpio:
            self.gpio = self.plugin_manager.get_plugin_by_id(self.gpio_name)
            self.read_args = self.plugin_manager.get_args(self.gpio, 'read_args')
            self.write_args = self.plugin_manager.get_args(self.gpio, 'write_args')

    def set_function(self, channel):
        """Sets the GPIO function."""
        if self.gpio and (channel not in self.current_functions or self.function != self.current_functions[channel]):
            function = getattr(self.gpio['instance'], self.gpio['set_function'])(channel, self.function).lower()
            self.current_functions[channel] = function
            if function == 'in':
                try:
                    debug('Register callback for channel {}'.format(channel))
                    getattr(self.gpio['instance'], self.gpio['register_callback'])(channel, self.data_changed, data=channel)
                except:
                    debug('Unable to register callback for channel {}'.format(channel))
                    pass

    def to_tuple(self, value):
        """Converts value to tuple with the appropriate data type."""
        data_type = 'digital_sensor'
        if (self.function == 'out'):
            data_type = 'digital_actuator'
        return (value, data_type)

    def read_value(self, channel):
        """Read the data value on the specified channel."""
        self.set_gpio()
        self.set_function(channel)
        try:
            value = getattr(self.gpio['instance'], self.gpio['read'])(channel, **self.read_args)
            value = int(value)
        except ValueError as e:
            debug(e)
            value = None
        return value

    def read(self, channel):
        """Gets the digital value for the channel as a tuple with the type."""
        return self.to_tuple(self.read_value(channel))

    def write_value(self, value, channel):
        """Write the data value on the specified channel."""
        self.set_gpio()
        self.set_function(channel)
        try:
            value = getattr(self.gpio['instance'], self.gpio['write'])(channel, int(value), **self.write_args)
        except ValueError as e:
            debug(e)
            value = None
        return value

    def write(self, value, channel):
        """Write the digital value for the channel."""
        return self.write_value(value, channel)

    def register_callback(self, callback):
        """Register a callback for data changes."""
        info('Registering callback: {}'.format(callback))
        self.callback = callback

    def unregister_callback(self):
        """Register a callback for data changes."""
        self.callback = None

    def data_changed(self, channel, value):
        """Callback that is called when data has changed."""
        if self.callback:
            self.callback(self.to_tuple(value))
