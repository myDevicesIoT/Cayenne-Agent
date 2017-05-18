from base64 import b64encode
from hashlib import sha256
from sys import version_info
PYTHON_MAJOR    = version_info.major
def encodeCredentials(login, password):
    abcd = "%s:%s" % (login, password)
    if PYTHON_MAJOR >= 3:
        b = b64encode(abcd.encode())
    else:
        b = b64encode(abcd)
    return b

def encrypt(value):
    return sha256(value).hexdigest()

def encryptCredentials(login, password):
    return encrypt(encodeCredentials(login, password))
