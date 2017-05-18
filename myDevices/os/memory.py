
# "Memory":{
#     "used": 377036800,
#     "total": 903979008,
#     "buffers": 129654784,
#     "cached": 135168000,
#     "processes": 112214016,
#     "free": 526942208,
#     "swap": {
#         "used": 0,
#         "free": 104853504,
#         "total": 104853504
#     }
# }
KB_MULTIPLIER = 1024.0
import mmap
class Memory:
    def __init__(self):
        self.file='/proc/meminfo'
        self.sep = ':'
        self.sep2 = ' '
        pass
    def get(self):
        memory = {}
        try:
            mapobject = {}
            with open(self.file, 'r') as f_stat:
                lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line != '']
                for line in lines:
                    mapobject[line[0]] = int(line[1].strip().split(self.sep2)[0])
            # print(mapobject)
            swap_free = mapobject["SwapFree"] * KB_MULTIPLIER
            memory['total'] =  mapobject["MemTotal"] * KB_MULTIPLIER
            memory['free'] = mapobject["MemAvailable"] * KB_MULTIPLIER
            memory['used'] = memory['total'] - memory['free']
            memory['buffers'] = mapobject["Buffers"] * KB_MULTIPLIER
            memory['cached'] = mapobject["Cached"] * KB_MULTIPLIER
            memory['processes'] = memory['used'] - memory['buffers'] - memory['cached']
            memory['swap'] = {}
            memory['swap']['total'] = mapobject["SwapTotal"] * KB_MULTIPLIER
            memory['swap']['free'] = mapobject["SwapFree"] * KB_MULTIPLIER
            memory['swap']['used'] = memory['swap']['total'] - memory['swap']['free']
        except Exception as e:
            print('Memory get error' + str(e))
        return memory


###################################
#test area
mem = Memory()
print(mem.get())
###################################


###################################

class Uptime:
    def __init__(self):
        self.file='/proc/uptime'
        self.sep = ' '
        pass
    def get(self):
        info = {}
        uptime      = 0.0
        idle        = 0.0
        try:
            with open(self.file, 'r') as f_stat:
                lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line != '']
                print(lines)
                uptime = float(lines[0][0])
                idle = float(lines[0][1])
        except Exception as e:
            print('Uptime exception:' + str(e))
        info['uptime']=uptime
        info['idle'] = idle
        return info

##############################
up = Uptime()
up.get()
##############################
