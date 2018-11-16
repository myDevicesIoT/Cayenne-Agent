"""
This module provides a class for interfacing with digital, analog and PWM plugins.
"""
from myDevices.plugins.manager import PluginManager
from myDevices.utils.logger import debug, info, exception


class InputOutput():
    """Reads/writes data from a digital, analog or PWM input/output plugin."""
    DATA_TYPES = {'digital': {'in': 'digital_sensor', 'out':'digital_actuator'},
        'analog': {'in': 'analog_sensor', 'out': 'analog_actuator'}}

    def __init__(self, plugin_id, io_type, function):
        """Initializes the analog input/output.
        
        Arguments:
            plugin_id: Extension plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
            io_type: The type of IO, 'analog' or 'digital'
            function: The pin function, 'in' if the pin is an input, 'out' if it is an output
        """
        self.plugin_id = plugin_id
        self.plugin = None
        self.io_type = io_type.lower()
        self.function = function.lower()
        self.current_functions = {}        
        self.read_args = {}
        self.write_args = {}        
        self.plugin_manager = PluginManager()
        self.set_plugin()
    
    def set_plugin(self):
        """Sets the plugin_id plugin."""
        if not self.plugin:
            self.plugin = self.plugin_manager.get_plugin_by_id(self.plugin_id)
            try:
                self.read_args = self.plugin_manager.get_args(self.plugin, 'read_args')
                self.write_args = self.plugin_manager.get_args(self.plugin, 'write_args')
            except:
                pass

    def set_function(self, channel):
        """Sets the input/output function."""
        try:
            if self.plugin and (channel not in self.current_functions or self.function != self.current_functions[channel]):
                function = getattr(self.plugin['instance'], self.plugin['set_function'])(channel, self.function).lower()
                self.current_functions[channel] = function
                if function == 'in':
                    try:
                        debug('Register callback for channel {}'.format(channel))
                        getattr(self.plugin['instance'], self.plugin['register_callback'])(channel, self.data_changed, data=channel)
                    except:
                        debug('Unable to register callback for channel {}'.format(channel))
                        pass
        except:
            debug('Error setting function')

    def to_tuple(self, value):
        """Converts value to tuple with the appropriate data type."""
        try:
            return (value, InputOutput.DATA_TYPES[self.io_type][self.function])
        except:
            return value

    def read(self, channel, data_type=None):
        """Gets the data value for the channel as a tuple with the type."""
        return self.to_tuple(self.read_value(channel, data_type))                

    def read_value(self, channel, data_type=None):
        """Read the data value on the specified channel."""
        self.set_plugin()
        self.set_function(channel)
        result = None
        try:
            result = getattr(self.plugin['instance'], self.plugin['read'])(channel, data_type=data_type, **self.read_args)
        except:
            info('Error reading value from plugin {}, channel {}, {}'.format(self.plugin_id, channel, self.plugin))
        return result

    def write(self, value, channel, data_type=None):
        """Write the digital value for the channel."""
        info('IO write, value {}, channel {}'.format(value, channel))
        return self.write_value(value, channel, data_type)

    def write_value(self, value, channel, data_type=None):
        """Write the data value on the specified channel."""
        self.set_plugin()
        self.set_function(channel)
        result = None
        try:
            result = getattr(self.plugin['instance'], self.plugin['write'])(channel, value, data_type=data_type, **self.write_args)
        except ValueError as e:
            debug(e)
        return result

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
