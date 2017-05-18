from myDevices.cloud.updater import Updater
from myDevices.utils.config import Config
from myDevices.cloud.client import APP_SETTINGS
from myDevices.utils.logger import setInfo

if __name__ == '__main__':
    # Run the actual update check in a script so it can be called via sudo
    setInfo()
    config = Config(APP_SETTINGS)
    updater = Updater(config)
    updater.DoUpdateCheck()
