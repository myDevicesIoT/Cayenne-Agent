"""
This module provides a plugin manager class for loading plugins and reading/writing plugin data.
"""
import fnmatch
import importlib
import json
import os
import sys

import myDevices.cloud.cayennemqtt as cayennemqtt
from myDevices.utils.config import Config
from myDevices.utils.logger import debug, error, exception, info


class PluginManager():
    """Loads plugins and reads/writes plugin data"""

    def __init__(self):
        """Initializes the plugin manager and loads the plugin list"""
        self.plugin_folder = '/etc/myDevices/plugins'
        self.plugins = {}
        self.load_plugins()
    
    def load_plugin_from_file(self, filename):
        """Loads a plugin from a specified plugin config file and adds it to the plugin list"""
        try:
            info('Loading plugin: {}'.format(filename))
            loaded = []
            config = Config(filename)
            plugin_name = os.path.splitext(os.path.basename(filename))[0]
            info('Sections: {}'.format(config.sections()))
            for section in config.sections():
                enabled = config.get(section, 'enabled', 'true').lower() == 'true'
                if enabled:
                    plugin = {
                        'channel': config.get(section, 'channel'),
                        'name': config.get(section, 'name', section),
                        'module': config.get(section, 'module'),
                        'class': config.get(section, 'class'),
                        'init_args': json.loads(config.get(section, 'init_args', '{}'))
                    }
                    folder = os.path.dirname(filename)
                    if folder not in sys.path:
                        sys.path.append(folder)
                    imported_module = importlib.import_module(plugin['module'])
                    device_class = getattr(imported_module, plugin['class'])
                    plugin['instance'] = device_class(**plugin['init_args'])
                    plugin['read'] = getattr(plugin['instance'], config.get(section, 'read'))
                    try:
                        plugin['write'] = getattr(plugin['instance'], config.get(section, 'write'))
                    except:
                        pass
                    self.plugins[plugin_name + ':' + plugin['channel']] = plugin
                    loaded.append(section)
        except Exception as e:
            error(e)
        info('Loaded sections: {}'.format(loaded))

    def load_plugins(self):
        """Loads plugins from any plugin config files found in the plugin folder"""
        for root, dirnames, filenames in os.walk(self.plugin_folder):
            for filename in fnmatch.filter(filenames, '*.plugin'):
                self.load_plugin_from_file(os.path.join(root, filename))

    def get_plugin_readings(self):
        """Return a list with current readings for all plugins"""
        readings = []
        for key, plugin in self.plugins.items():
            try:
                value = plugin['read']()
                value_dict = self.convert_to_dict(value)
                if value_dict:
                    cayennemqtt.DataChannel.add(readings, cayennemqtt.DEV_SENSOR, key, name=plugin['name'], **value_dict)
            except KeyError as e:
                debug('Missing key {} in plugin \'{}\''.format(e, plugin['name']))
            except:
                exception('Error reading from plugin \'{}\''.format(plugin['name']))
        return readings

    def convert_to_dict(self, value):
        """Convert a tuple value to a dict containing value, type and unit"""
        value_dict = {}
        try:
            if value is None or value[0] is None:
                return value_dict
            value_dict['value'] = value[0]
            value_dict['type'] = value[1]
            value_dict['unit'] = value[2]
        except:
            if not value_dict:
                value_dict['value'] = value
            if 'type' in value_dict and 'unit' not in value_dict:
                if value_dict['type'] == 'digital_actuator':
                    value_dict['unit'] = 'd'
                elif value_dict['type'] == 'analog_actuator':
                    value_dict['unit'] = 'null'
        return value_dict

    def is_plugin(self, plugin, channel):
        """Returns True if the specified plugin:channel is a valid plugin"""
        return plugin + ':' + channel in self.plugins.keys()

    def write_value(self, plugin, channel, value):
        """Write a value to a plugin actuator.
        
        Returns: True if value written, False if it was not"""
        actuator = plugin + ':' + channel
        info('Write value {} to {}'.format(value, actuator))
        if actuator in self.plugins.keys():
            try:
                self.plugins[actuator]['write'](float(value))
            except:
                return False
        else:
            return False
        return True