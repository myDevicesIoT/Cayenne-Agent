import sys
from myDevices.utils.config import Config
from myDevices.utils.logger import setInfo, info, error
from myDevices.plugins.manager import PLUGIN_FOLDER

if __name__ == '__main__':
    # Run the code to disable a plugin in a script so it can be called via sudo
    setInfo()
    info(sys.argv)
    if len(sys.argv) != 3:
        error('Plugin not disabled, invalid arguments')
        sys.exit(1)
    filename = sys.argv[1]
    if filename.startswith(PLUGIN_FOLDER) and filename.endswith('.plugin'):
        section = sys.argv[2]
        config = Config(filename)
        if section in config.sections():
            config.set(section, 'enabled', 'false')
        else:
            error('Section \'{}\' not found in {}'.format(section, filename))
            sys.exit(1)
    else:
        sys.exit(1)
