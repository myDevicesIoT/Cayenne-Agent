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
from myDevices.utils.subprocess import executeCommand

PLUGIN_FOLDER = '/etc/myDevices/plugins'


class PluginManager():
    """Loads plugins and reads/writes plugin data"""

    def __init__(self):
        """Initializes the plugin manager and loads the plugin list"""
        self.plugin_folder = PLUGIN_FOLDER
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
                try:
                    enabled = config.get(section, 'enabled', 'true').lower() == 'true'
                    inherit = config.get(section, 'inherit', None)
                    if enabled:
                        plugin = {
                            'filename': filename,
                            'section': section,
                            'channel': config.get(section, 'channel'),
                            'name': config.get(section, 'name', section)
                        }
                        inherit_items = {}
                        if inherit in config.sections():
                            if inherit == section:
                                raise ValueError('Section \'{}\' cannot inherit from itself'.format(section))
                            inherit_from = self.get_plugin(filename, inherit)
                            inherit_items = {key:value for key, value in inherit_from.items() if key not in plugin.keys()}
                            plugin.update(inherit_items)
                        elif inherit:
                            raise ValueError('Section \'{}\' cannot inherit from \'{}\'. Check spelling and section ordering.'.format(section, inherit))
                        self.override_plugin_value(config, section, 'module', plugin)
                        self.override_plugin_value(config, section, 'class', plugin)
                        if 'init_args' not in plugin:
                            plugin['init_args'] = '{}'
                        self.override_plugin_value(config, section, 'init_args', plugin)
                        if not inherit_items or [key for key in ('module', 'class', 'init_args') if inherit_items[key] is not plugin[key]]:
                            info('Creating instance of {} for {}'.format(plugin['class'], plugin['name']))
                            folder = os.path.dirname(filename)
                            if folder not in sys.path:
                                sys.path.append(folder)
                            imported_module = importlib.import_module(plugin['module'])
                            device_class = getattr(imported_module, plugin['class'])
                            plugin['instance'] = device_class(**json.loads(plugin['init_args']))
                        self.override_plugin_value(config, section, 'read', plugin)
                        try:
                            self.override_plugin_value(config, section, 'write', plugin)
                        except:
                            pass
                        self.plugins[plugin_name + ':' + plugin['channel']] = plugin
                        loaded.append(section)
                except Exception as e:
                    error(e)
        except Exception as e:
            error(e)
        info('Loaded sections: {}'.format(loaded))

    def load_plugins(self):
        """Loads plugins from any plugin config files found in the plugin folder"""
        for root, dirnames, filenames in os.walk(self.plugin_folder):
            for filename in fnmatch.filter(filenames, '*.plugin'):
                self.load_plugin_from_file(os.path.join(root, filename))

    def get_plugin(self, filename, section):
        """Return the plugin for the corresponding filename and section"""
        return next(plugin for plugin in self.plugins.values() if plugin['filename'] == filename and plugin['section'] == section)

    def override_plugin_value(self, config, section, key, plugin):
        """Override the plugin value for the specified key if it exists in the config file"""
        if key not in plugin:
            plugin[key] = config.get(section, key)
        else:
            plugin[key] = config.get(section, key, plugin[key])

    def get_plugin_readings(self):
        """Return a list with current readings for all plugins"""
        readings = []
        for key, plugin in self.plugins.items():
            try:
                value = getattr(plugin['instance'], plugin['read'])()
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

    def is_plugin(self, plugin, channel=None):
        """Returns True if the specified plugin or plugin:channel are valid plugins"""
        try:
            key = plugin
            if channel is not None:
                key = plugin + ':' + channel
            return key in self.plugins.keys()
        except:
            return False

    def write_value(self, plugin, channel, value):
        """Write a value to a plugin actuator.
        
        Returns: True if value written, False if it was not"""
        actuator = plugin + ':' + channel
        info('Write value {} to {}'.format(value, actuator))
        if actuator in self.plugins.keys():
            try:
                write_function = getattr(self.plugins[actuator]['instance'], self.plugins[actuator]['write'])
                write_function(float(value))
            except:
                return False
        else:
            return False
        return True

    def disable(self, plugin):
        """Disable the specified plugin"""
        disabled = False
        try:
            output, result = executeCommand('sudo python3 -m myDevices.plugins.disable "{}" "{}"'.format(self.plugins[plugin]['filename'], self.plugins[plugin]['section']))
            if result == 0:
                disabled = True
                info('Plugin \'{}\' disabled'.format(plugin))
            else:
                info('Plugin \'{}\' not disabled'.format(plugin))
            del self.plugins[plugin]
        except Exception as e:
            info(e)
            pass
        return disabled