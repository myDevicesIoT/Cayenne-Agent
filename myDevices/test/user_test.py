import pwd
import os

try:
    user = pwd.getpwnam('cayenne')
    user_id = user.pw_uid
    group_id = user.pw_gid
except KeyError:
    user_id = os.environ['SUDO_UID']
    group_id = os.environ['SUDO_GID']
print(user_id)
print(group_id)
