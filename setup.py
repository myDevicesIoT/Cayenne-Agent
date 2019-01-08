from setuptools import setup, Extension
import os
import pwd
import grp
from myDevices import __version__
from myDevices.system.hardware import Hardware


classifiers = ['Development Status :: 5 - Production/Stable',
               'Operating System :: POSIX :: Linux',
               'License :: OSI Approved :: MIT License',
               'Intended Audience :: Developers',
               'Programming Language :: Python :: 3',
               'Topic :: Software Development',
               'Topic :: Home Automation',
               'Topic :: System :: Hardware',
               'Topic :: System :: Monitoring']

try:
    # Try to install under the cayenne user, if it exists.
    username = 'cayenne'
    user = pwd.getpwnam(username)
    user_id = user.pw_uid
    group_id = user.pw_gid
except KeyError:
    # Otherwise install under the user that ran sudo.
    user_id = int(os.environ['SUDO_UID'])
    group_id = int(os.environ['SUDO_GID'])
    username = pwd.getpwuid(user_id).pw_name
directories = ('/etc/myDevices', '/etc/myDevices/scripts', '/etc/myDevices/plugins', '/var/log/myDevices', '/var/run/myDevices')
for directory in directories:
    try:
        os.makedirs(directory)
    except FileExistsError:
        pass
    os.chown(directory, user_id, group_id)

# Touch config file so it overwrites older versions
os.utime('scripts/config.sh', None)

setup(name             = 'myDevices',
      version          = __version__,
      author           = 'myDevices',
      author_email     = 'N/A',
      description      = 'myDevices Cayenne agent',
      long_description = 'N/A',
      license          = 'N/A',
      keywords         = 'myDevices Cayenne IoT',
      url              = 'https://www.mydevices.com/',
      classifiers      = classifiers,
      packages         = ["myDevices", "myDevices.cloud", "myDevices.utils", "myDevices.system", "myDevices.sensors" , "myDevices.schedule", "myDevices.requests_futures", "myDevices.devices", "myDevices.devices.analog", "myDevices.devices.digital", "myDevices.devices.sensor", "myDevices.decorators", "myDevices.plugins"],
      install_requires = ['enum34', 'jsonpickle', 'netifaces >= 0.10.5', 'psutil >= 0.7.0', 'requests', 'paho-mqtt'],
      data_files       = [('/etc/myDevices/scripts', ['scripts/config.sh'])]
      )

os.chmod('/etc/myDevices/scripts/config.sh', 0o0755)

# Add conf file to create /var/run/myDevices at boot
with open('/usr/lib/tmpfiles.d/cayenne.conf', 'w') as tmpfile:
    tmpfile.write('d /run/myDevices 0744 {0} {0} -\n'.format(username))

relogin = False
# Add user to the i2c group if it isn't already a member
user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
if not 'i2c' in user_groups:
    os.system('adduser {} i2c'.format(username))
    relogin = True

if Hardware().isTinkerBoard():
    # Add spi group if it doesn't exist
    all_groups = [g.gr_name for g in grp.getgrall()]
    if not 'spi' in all_groups:
        os.system('groupadd -f -f spi')
        os.system('adduser {} spi'.format(username))
        with open('/etc/udev/rules.d/99-com.rules', 'w') as spirules:
            spirules.write('SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"\n') 
        os.system('udevadm control --reload-rules && udevadm trigger')
        relogin = True
    # Install GPIO library if it doesn't exist
    try:
        import ASUS.GPIO
    except:
        current_dir = os.getcwd()
        try:
            TEMP_FOLDER = '/tmp/GPIO_API_for_Python'
            GPIO_API_ZIP = TEMP_FOLDER + '.zip'
            import urllib.request
            print('Downloading ASUS.GPIO library')
            urllib.request.urlretrieve('http://dlcdnet.asus.com/pub/ASUS/mb/Linux/Tinker_Board_2GB/GPIO_API_for_Python.zip', GPIO_API_ZIP)
            import zipfile
            with zipfile.ZipFile(GPIO_API_ZIP, 'r') as lib_zip:
                lib_zip.extractall(TEMP_FOLDER)
                os.chdir(TEMP_FOLDER)
                import distutils.core
                print('Installing ASUS.GPIO library')
                distutils.core.run_setup(TEMP_FOLDER + '/setup.py', ['install'])
        except Exception as ex:
            print('Error installing ASUS.GPIO library: {}'.format(ex))
        finally:
            os.chdir(current_dir)       

if relogin:
    print('\nYou may need to re-login in order to use I2C or SPI devices')
