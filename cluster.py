import re
import socket
from logging import debug, info
from os import kill, popen3
from popen2 import Popen4
import time
import signal

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

TIMEOUT = 60

def handleAlarm(sigNum, stackFrame):
    info('timed out')
    try:
        kill(p.pid, signal.SIGHUP)
    except:
        debug('couldnt kill pid')

def startAlarm():
    signal.signal(signal.SIGALRM, handleAlarm)
    signal.alarm(TIMEOUT)

def stopAlarm():
    signal.alarm(0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)

def isZeoServerRunning():
    info('trying zeo server %s', MASTER)
    cmd = 'ssh %s zdctl.py -C %s/server/zdctl.conf status 2>&1'%(MASTER, INSTDIR)
    debug(cmd)
    startAlarm()
    p = Popen4(cmd)
    s = p.fromchild.read().strip()
    stopAlarm()
    debug(s)
    running = re.match(r'.* running .*', s) and not re.match(r'.* not running.*', s)
    if running:
        info('zeo server is running')
    else:
        info('zeo server is not running')
    return running

def startZeoServer():
    running = isZeoServerRunning()
    if not running:
        info('starting zeo server')
        _,_,_ = popen3('ssh %s make -C %s startserver'%(MASTER, INSTDIR))
        time.sleep(5)
    
def stopZeoServer():
    running = isZeoServerRunning()
    if running:
        info ('stopping zeo server')
        _,_,_ = popen3('ssh %s make -C %s stopserver'%(MASTER, INSTDIR))

def getZeoClientPid(host):
    info('trying zeo client %s', host)
    startAlarm()
    p = Popen4('ssh -f %s cat /tmp/client.pid 2>&1'%host)
    s = p.fromchild.read().strip()
    stopAlarm()
    debug('recv: %s',s)
    if s.find('No such file') > -1:
        info('/tmp/client.pid not found')
        return 0
    elif s.find('Connection reset by peer') > -1:
        info(s)
        return -1
    else:
        try:
            pid = int(s)
            debug('client pid: %d', pid)
            return pid
        except Exception, e:
            info('%s %s', e, s)
            debug(e)
            return -1

def getZeoClientDetails(host, pid):
    cmd = 'ssh %s ps -p %d'%(host, pid)
    debug('send: %s', cmd)
    _,stdout,_ = popen3(cmd)
    s1 = stdout.read()
    debug('recv: %s', s1)
    m = re.match('\s*PID\s+TTY\s+TIME\s+CMD\s+\d+\s*[\w?]*\s+([\d:]+)\s+(\w+)',s1)
    if m:
        cpu = m.group(1)
        comm = m.group(2)
        info('Process %s running on host %s with elapsed cpucpu %s (h:m:s)'%(comm,host,cpu))
        return (cpu, comm)
    else:
        debug('Process on %s seems to have died!'%host)
        return None

def startZeoClient(host, run=None):
    try:
        restart = 0
        pid = getZeoClientPid(host)
        if pid == 0:
            restart = 1
        elif pid > 0:
            details = getZeoClientDetails(host, pid)
            if not details:
                restart = 1
        if restart:
            if host == MASTER:
                opt = '-m'
                s = 'master'
            else:
                opt = '-c'
                s = 'slave'
            info('Restarting %s client on %s', s, host)
            cmd = 'ssh %s /bin/nice -n 5 %s/src/ev.py -z %s -b %s'%(host, INSTDIR, MASTER, opt)
            if run:
                cmd += ' -r %s'%run
            debug(cmd)
            _,_,_ = popen3(cmd)
    except IOError, e:
        debug('ioerror %s', e)

def startZeoClients(hosts=HOSTS, run=None):
    for host in hosts:
        startZeoClient(host, run)

def stopZeoClient(host):
    try:
        pid = getZeoClientPid(host)
        if pid > 0:
            cmd = 'ssh %s kill %d'%(host, pid)
            info('killing..')
            p = Popen4('ssh %s "kill %d; rm /tmp/client.pid; echo killed by cluster.py at `date` >> /tmp/client.stderr"'%(host, pid))
            s = p.fromchild.read()
            debug('recv: %s',s)
    except IOError, e:
        debug('ioerror %s', e)

def stopZeoClients(hosts=HOSTS):
    for host in hosts:
        stopZeoClient(host)
