import re
import socket

CLUSTER = 'bw64'
HOME = '/home/s9734229'
INSTDIR = HOME + '/phd'
MASTER = CLUSTER + 'node01'
REGEXP = r'bw240n\d\d.inf.ed.ac.uk'

def nodeName(n):
    return CLUSTER + 'node' + str(n).zfill(2)

HOSTS = [nodeName(x) for x in range(1,65)]
HOSTNAMES = [ 'bw240n%s'%(str(x).zfill(2)) for x in range(1,65) ] + ['bob']

def isHost():
    if re.match(REGEXP,  socket.gethostname()):
        return 1
    return 0

def getHostname():
    s = socket.gethostname()
    i = s.find('.')
    if i == -1:
        return s
    else:
        return s[:i]
