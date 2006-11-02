import re
import socket

CLUSTER = 'bw64'
HOME = '/home/s9734229'
INSTDIR = HOME + '/phd'
MASTER = CLUSTER + 'node01'
REGEXP = r'bw240n\d\d.inf.ed.ac.uk'

def nodeName(x):
    return CLUSTER + 'node' + str(x).zfill(2)

def isHost():
    if re.match(REGEXP,  socket.gethostname()):
        return 1
    return 0

hosts = [nodeName(x) for x in range(1,65)]
