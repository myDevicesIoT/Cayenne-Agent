"""
This module contains code to retrieve the OS version.
"""
OS_VERSION = 0
OS_WHEEZY = 1
OS_JESSIE = 2
OS_STRETCH = 3

try:
    with open("/etc/apt/sources.list") as f:
        sources = f.read()
        if "wheezy" in sources:
            OS_VERSION = OS_WHEEZY
        elif "jessie" in sources:
            OS_VERSION = OS_JESSIE
        elif "stretch" in sources:
            OS_VERSION = OS_STRETCH
except:
    pass
