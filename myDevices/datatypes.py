"""This module provides a script for getting the available data types and units that can be used with Cayenne."""

import sys
import inspect
from myDevices.cloud.apiclient import CayenneApiClient

if __name__ == "__main__":
    args = sys.argv[1:]
    if '--help' in args or '-h' in args:
        print('Usage: python3 -m myDevices.datatypes [-h] [PATTERN ...]\n\n'
            'Search for PATTERN in any of the available Cayenne data types and units.\n'
            'If no PATTERN is specified all available data types and units are displayed.\n'
            'The case of PATTERN is ignored.\n\n'
            'Example: python3 -m myDevices.datatypes temp humidity\n\n'
            'Options:\n'
            '    -h, --help       Display this help message and exit')
        sys.exit()
    api_client = CayenneApiClient('https://api.mydevices.com')
    data_types = api_client.getDataTypes().json()
    if 'error' in data_types:
        print('Error {}. Could not retrieve data types. Please try again later.'.format(data_types['statusCode']))
        sys.exit()
    output = []
    for data_type in data_types:
        # Ignore LT100GPS type since that is a custom type that is not intended for general use.
        if data_type['data_type'] != 'LT100GPS':
            units = ''
            for unit in data_type['units']:
                payload_unit = unit['payload_unit'] if unit['payload_unit'] else 'null'
                units += ('\'{}\' ({}), '.format(payload_unit, unit['unit_label']))
            units = units[:-2]
            entry = '{}\n   Type: \'{}\'\n   Units: {}\n'.format(data_type['data_type'], data_type['payload_type'], units)
            if not args:
                output.append(entry)
            else:
                for arg in args:
                    if entry.lower().find(arg.lower()) != -1:
                        output.append(entry)
    output.sort(key=lambda x: x.lower())
    for item in output:
        print(item)