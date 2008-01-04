#!/usr/bin/python

import db, transaction, random, logging, os, sys, time, traceback
import time, popen2, re, copy, thread, fcntl, socket
from logging import debug, error
from ZODB.FileStorage import FileStorage
from ZODB import DB, POSException
from ConfigParser import SafeConfigParser

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('ZEO').setLevel(logging.INFO)
config = SafeConfigParser()
config.read(os.path.expanduser('~/.ev'))
donedir = config.get('cluster','donedir') # must be absolute path, not ~/...
if donedir[-1] != '/':
    donedir += '/'
zeofile = None
if config.has_option('cluster','zeofile'):
    zeofile = os.path.expanduser(config.get('cluster','zeofile'))
tmp = os.environ.get('TMPDIR')
if not tmp:
    tmp = '/tmp/'
if config.has_option('cluster','tmpdir'):
    tmp = config.get('cluster','tmpdir')
if tmp[-1] != '/':
    tmp += '/'
tmp += socket.gethostname()+'/'
try:
    if not os.path.exists(tmp):
        os.mkdir(tmp)
except:
    pass
pat = r'[pb]\d\d\d$'
pretend = 0
if '-p' in sys.argv:
    pretend = 1

def lsdone():
    s = 'rsync %s'%donedir
    debug('%s', s)
    o,i = popen2.popen2(s)
    files = [x.split(' ')[-1][:-1] for x in o.readlines()]
    done = [x for x in files if re.match(pat, x)]
    debug('done %s', done)
    return done

def monitor(zodb):
    r = zodb[-4:]
    while 1:
        time.sleep(10*60)
        debug('monitor wakeup %s'%r)
        done = lsdone()
        if r in done:
            debug('monitor kill process %s', r)
            os.system('pkill -f %s'%zodb)
            return

def bad(z):
    r = z[-4:]
    try:
        c = DB(FileStorage(z)).open()
        root = c.root()
        if root.has_key(r):
            e = 0
            debug('good %s', z)
        else:
            e = 1
            debug('bad %s (key %s missing)', z, r)
        c.close()
        c.db().close()
    except IOError:
        debug('good %s (busy)', z)
        e = 0
    except Exception:
        debug('bad zodb %s (corrupt)', z)
        e = 1
    return e

lockfile = None

def lock(z):
    try:
        global lockfile
        lockfile = open('%s.golock'%z, 'w')
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
    except IOError:
        lockfile.close()
        lockfile = None
        return 0
    return 1

def unlock():
    global lockfile
    if lockfile:
        lockfile.close()
        lockfile = None

while 1:
    try:
        unlock()
        debug('ls done')
        dl = open(tmp+'done.golock','w')
        fcntl.flock(dl.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
        done = lsdone()
        oldruns = [x for x in os.listdir(tmp) if re.match(pat,x)] #  and os.stat(tmp+x).st_mtime < time.time()-5*60]
        debug('oldruns %s', oldruns)
        orc = oldruns[:]
        random.shuffle(orc)
        busyl = []
        for x in orc:
            if lock(tmp+x):
                broke = bad(tmp+x)
                if x in done or broke:
                    if broke: reason = 'bad'
                    if x in done: reason = 'done'
                    debug('%s %s, removing..', reason, tmp+x)
                    if not pretend:
                        os.unlink('%s'%(tmp+x))
                    oldruns.remove(x)
                unlock()
            else:
                debug('%s is busy',tmp+x)
                oldruns.remove(x)
                busyl.append(x)
        # oldruns now contains potentially valid runs
        zodb = None
        if oldruns:
            debug('valid oldruns %s', oldruns)
            name = random.choice(oldruns)
            zodb = tmp+name
            if not lock(zodb):
                continue
            debug('resume %s', zodb)
            dl.close()
        else:
            debug('db.connect')
            if zeofile:
                while not lock(zeofile):
                    debug('busy ZEO file...')
                    time.sleep(random.randint(2,15))
                root = db.connect(zodb=zeofile)
            else:
                root = db.connect()
            r = [x for x in root['runs'] if x.name not in done and x.name not in busyl]
            assert len(r) == len(set(r)-set(done))
            if not r:
                debug('all done')
                break
            c = random.choice(r)
            c.taken += 1
            debug('db.close')
            c = copy.deepcopy(c) # don't use persistent object after db close
            transaction.abort() # DB keeps getting corrupted!!
            db.close()
            unlock()
            debug('run %s', c.name)
            assert c.name not in done
            zodb = tmp+c.name
            if not lock(zodb):
                continue
            debug('create %s', zodb)
            dl.close()
            if not pretend:
                s = '%s -f %s'%(c.cl, zodb)
                debug(s)
                e = os.system(s)
                if e:
                    error('child process failed')
                    continue
        s = 'ev -f %s -c -m'%(zodb)
        debug(s)
        if not pretend:
            thread.start_new_thread(monitor, (zodb,))
            e = os.system(s)
            if e:
                error('child process failed')
                continue
        debug('pack %s', zodb)
        if not pretend:
            FileStorage(zodb).pack(time.time(), None)
        s = 'rsync -av %s %s'%(zodb, donedir)
        debug(s)
        if not pretend and not bad(zodb):
            e = os.system(s)
            if not e:
                os.unlink(zodb)
    except Exception, e:
        error('%s', traceback.format_exc())
        time.sleep(5)
