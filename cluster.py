import re
import socket
import os
from logging import debug, info
import popen2
import time
import signal
from ConfigParser import SafeConfigParser

# This code used to be important since clients were started on each host
# individually using tentakel, or from an ssh script, and then had to make sure
# they were the only client process on that host, restart clients and the server
# if necessary, etc.
# With the new Grid Engine batch management system most of that is handled
# automatically, and since we have no direct ssh access to clients anymore, this
# code is mostly obsolete.

CLUSTER = 'bw64'
HOME = '/home/s9734229'
INSTDIR = HOME + '/phd'
MASTER = CLUSTER + 'node02'
REGEXP = r'bw240n\d\d.inf.ed.ac.uk'
config = SafeConfigParser()
config.read(os.path.expanduser('~/.ev'))
try:
    ZEOSERVER = config.get('cluster','zeoserver')
except:
    debug('no ZEO server')

def getBadHosts():
    # bad host list in tentakel.conf looks like '# BAD: host1 host2'
    p = os.path.expanduser('~/.tentakel/tentakel.conf')
    bad = []
    if os.path.exists(p):
        f = open(p)
        s = f.readlines()
        for l in s:
            if '# BAD:' in l:
                i = 6
                while 1:
                    m = re.search(r'bw64node\d\d', l[i:])
                    if not m:
                        break
                    bad.append(m.group())
                    i += m.end()
    return bad

def nodeName(n):
    return CLUSTER + 'node' + str(n).zfill(2)

HOSTS = list(set([nodeName(x) for x in range(2,65)]) - set(getBadHosts()))
HOSTS.sort()
def bwlist(prefix,n):
    return [ '%sn%s'%(prefix,str(x).zfill(2)) for x in range(1,n) ]
HOSTNAMES = bwlist('bw240',65) + ['bob']
HOSTNAMES += ['lutzow']
HOSTNAMES += ['hermes'] + bwlist('bw1425',25)

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
p = None # current executing Popen4 process for alarm handler

def popen(server, cmd):
    global p
    if server != 'localhost':
        cmd = 'ssh -f %s "%s"'%(server, cmd)
    p = popen2.Popen4(cmd)

def handleAlarm(sigNum, stackFrame):
    info('timed out')
    try:
        os.kill(p.pid, signal.SIGHUP)
    except:
        debug('couldnt kill pid')

def startAlarm():
    signal.signal(signal.SIGALRM, handleAlarm)
    signal.alarm(TIMEOUT)

def stopAlarm():
    signal.alarm(0)
    signal.signal(signal.SIGALRM, signal.SIG_DFL)

def isZeoServerRunning():
    info('trying zeo server %s', ZEOSERVER)
    cmd = 'cd %s/server && make status 2>&1'%(INSTDIR)
    debug(cmd)
    startAlarm()
    popen(ZEOSERVER, cmd)
    s = p.fromchild.read().strip()
    stopAlarm()
    debug(s)
    running = not re.search(r'not running', s) and 'failure' not in s
    if running:
        info('zeo server is running')
    else:
        info('zeo server is not running')
    return running

def startZeoServer():
    running = isZeoServerRunning()
    if not running:
        info('starting zeo server')
        popen(ZEOSERVER, 'make -C %s startserver'%INSTDIR)
        time.sleep(5)

def stopZeoServer():
    running = isZeoServerRunning()
    if running:
        info ('stopping zeo server')
        popen(ZEOSERVER, 'make -C %s stopserver'%INSTDIR)

def getZeoClientPid(host):
    info('trying zeo client %s', host)
    startAlarm()
    popen(host, 'cat /tmp/client.pid 2>&1')
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
    cmd = 'ps -p %d'%pid
    debug('send: %s', cmd)
    popen(host, cmd)
    s1 = p.fromchild.read()
    debug('recv: %s', s1)
    m = re.match('\s*PID\s+TTY\s+TIME\s+CMD\s+\d+\s*[\w?]*\s+([\d:]+)\s+(\w+)',s1)
    if m:
        cpu = m.group(1)
        comm = m.group(2)
        info('Process %s running on host %s with elapsed cpu %s (h:m:s)'%(comm,host,cpu))
        return (cpu, comm)
    else:
        debug('Process on %s seems to have died!'%host)
        return None

def startZeoClient(host, run=None, single=0):
    try:
        restart = 0
        pid = getZeoClientPid(host)
        if pid == -1:
            return -1
        elif pid == 0:
            restart = 1
        elif pid > 0:
            details = getZeoClientDetails(host, pid)
            if not details:
                restart = 1
        if restart:
            if single:
                opt = '-m -c'
                s = 'single host (debug/devel): master and client'
            elif host == MASTER:
                opt = '-m'
                s = 'master'
            else:
                opt = '-c'
                s = 'slave'
            info('Restarting %s client on %s', s, host)
            cmd = 'nice -n 5 %s/src/ev.py -z %s -b %s'%(INSTDIR, ZEOSERVER, opt)
            if run:
                cmd += ' -r %s'%run
            debug(cmd)
            popen(host, cmd)
        return 0
    except IOError, e:
        debug('ioerror %s', e)
        return -1

def startZeoClients(hosts=HOSTS, run=None):
    single = 0
    if len(hosts) == 1:
        single = 1
    h = []
    for host in hosts:
        e = startZeoClient(host, run, single)
        if e == 0:
            h.append(host)
    return h

def stopZeoClient(host):
    try:
        pid = getZeoClientPid(host)
        if pid > 0:
            info('killing..')
            popen(host, 'kill %d; rm /tmp/client.pid; echo killed by cluster.py at `date` >> /tmp/client.stderr'%pid)
            s = p.fromchild.read()
            debug('recv: %s',s)
    except IOError, e:
        debug('ioerror %s', e)

def stopZeoClients(hosts=HOSTS):
    for host in hosts:
        stopZeoClient(host)
