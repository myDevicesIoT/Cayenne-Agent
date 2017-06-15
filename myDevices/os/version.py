"""
This module contains code to retrieve the OS version.
"""
OS_VERSION = 0
OS_RASPBIAN_WHEEZY = 1
OS_RASPBIAN_JESSIE = 2

try:
    with open("/etc/apt/sources.list") as f:
        sources = f.read()
        if "wheezy" in sources:
            OS_VERSION = OS_RASPBIAN_WHEEZY
        elif "jessie" in sources:
            OS_VERSION = OS_RASPBIAN_JESSIE
except:
    pass
