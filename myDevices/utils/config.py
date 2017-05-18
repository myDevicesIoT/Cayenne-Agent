from configparser import RawConfigParser, _UNSET, NoSectionError
from threading import RLock

class Config:
    def __init__(self, path):
        self.mutex = RLock()
        self.path = path
        self.config = RawConfigParser()
        self.config.optionxform = str
        self.cloudConfig = {}
        try:
            with open(path) as fp:
                self.config.readfp(fp)
        except:
            pass
    def set(self, section, key, value):
        with self.mutex:
            try:
                self.config.set(section, key, value)
            except NoSectionError:
                self.config.add_section(section)
                self.config.set(section, key, value)
        return self.save()

    def get(self, section, key, fallback=_UNSET):
        return self.config.get(section, key, fallback=fallback)

    def getInt(self, section, key, fallback=_UNSET):
        return self.config.getint(section, key, fallback=fallback)

    def save(self):
        with self.mutex:
            with open(self.path, 'w') as configfile:
                self.config.write(configfile)

    def sections(self):
        return self.config.sections()

    def setCloudConfig(self, cloudConfig):
        self.cloudConfig = cloudConfig


