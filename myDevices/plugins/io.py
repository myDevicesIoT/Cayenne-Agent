"""
This module provides a class for interfacing with digital, analog and PWM plugins.
"""
from myDevices.plugins.manager import PluginManager
from myDevices.utils.logger import debug, info, exception


class InputOutput():
    """Reads data from and writes data to an input/output plugin."""

    def __init__(self, plugin_id, function, data_type):
        """Initializes the input/output.
        
        Arguments:
            plugin_id: Extension plugin ID in the format 'plugin_name:section', e.g. 'cayenne-pca9685:PCA9685'
            function: The IO function, 'in' or 'out'
            data_type: The Cayenne data type, e.g. 'digital_sensor'
        """
        self.plugin_id = plugin_id
        self.plugin = None
        self.data_type = data_type.lower()
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

    def value_to_tuple(self, value):
        """Converts value to tuple with the appropriate Cayenne data type."""
        return (value, self.data_type)

    def read(self, channel, value_type=None):
        """Gets the data value for the channel as a tuple with the type."""
        return self.value_to_tuple(self.read_value(channel, value_type))                

    def read_value(self, channel, value_type=None):
        """Read the data value on the specified channel."""
        self.set_plugin()
        self.set_function(channel)
        result = None
        try:
            read_args = self.read_args
            if value_type:
                read_args['value_type'] = value_type
            result = getattr(self.plugin['instance'], self.plugin['read'])(channel, **read_args)
        except:
            exception('Error reading value from plugin {}, channel {}, {}'.format(self.plugin_id, channel, self.plugin))
        return result

    def write(self, value, channel, value_type=None):
        """Write the digital value for the channel."""
        return self.write_value(value, channel, value_type)

    def write_value(self, value, channel, value_type=None):
        """Write the data value on the specified channel."""
        self.set_plugin()
        self.set_function(channel)
        result = None
        try:
            write_args = self.write_args
            if value_type:
                write_args['value_type'] = value_type            
            result = getattr(self.plugin['instance'], self.plugin['write'])(channel, value, **write_args)
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
            self.callback(self.value_to_tuple(value))
