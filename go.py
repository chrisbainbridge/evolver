#!/usr/bin/python

import db, transaction, random, logging, os, sys, time, traceback
import time, popen2, re, copy, thread, fcntl
from logging import debug, error
from ZODB.FileStorage import FileStorage
from ZODB import DB
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
tmp = '/tmp/'
if config.has_option('cluster','tmpdir'):
    tmp = config.get('cluster','tmpdir')
if tmp[-1] != '/':
    tmp += '/'
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
    c = DB(FileStorage(z)).open()
    root = c.root()
    e = 1
    if root.has_key(r) and root[r].gen_num >= 1:
        e = 0
    debug('%s bad=%d', z, e)
    c.close()
    c.db().close()
    return e

def busy(z):
    try:
        f = open('%s.lock'%z, 'w')
        fcntl.flock(f.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
    except IOError:
        return 1
    return 0

while 1:
    try:
        debug('ls done')
        done = lsdone()
        oldruns = [x for x in os.listdir(tmp) if re.match(pat,x) and os.stat(tmp+x).st_mtime < time.time()-5*60]
        debug('oldruns %s', oldruns)
        orc = oldruns[:]
        random.shuffle(orc)
        for x in orc:
            if busy(tmp+x):
                debug('%s is busy',tmp+x)
                oldruns.remove(x)
            elif x in done or bad(x):
                debug('rm oldrun %s',tmp+x)
                if not pretend:
                    os.unlink('%s'%(tmp+x))
                oldruns.remove(x)
        # oldruns now contains potentially valid runs
        if oldruns:
            debug('valid oldruns %s', oldruns)
            zodb = tmp+random.choice(oldruns)
        else:
            debug('db.connect')
            if zeofile:
                while busy(zeofile):
                    debug('busy ZEO file...')
                    time.sleep(random.randint(2,15))
                root = db.connect(zodb=zeofile)
            else:
                root = db.connect()
            r = [x for x in root['runs'] if x not in done]
            if not r:
                debug('all done')
                break
            # note: this scheduling is suboptimal - would be better to use
            # timestamps and just choose and update the oldest one
            m = min([x.taken for x in r])
            l = [x for x in r if x.taken == m]
            c = random.choice(l)
            c.taken += 1
            if not pretend:
                transaction.commit()
            debug('db.close')
            c = copy.deepcopy(c) # don't use persistent object after db close
            db.close()
            debug('run %s', c.name)
            zodb = tmp+c.name
            debug('create %s', zodb)
            if os.path.exists(zodb):
                os.unlink(zodb)
            if not pretend:
                s = '%s -f %s'%(c.cl, zodb)
                debug(s)
                e = os.system(s)
                if e:
                    error('child process failed')
                    continue
        debug('eval file: %s', zodb)
        if not pretend:
            thread.start_new_thread(monitor, (zodb,))
            e = os.system('ev -f %s -c -m'%(zodb))
            if e:
                error('child process failed')
                continue
        debug('pack %s', zodb)
        if not pretend:
            FileStorage(zodb).pack(time.time(), None)
        debug('rsync %s %s', zodb, donedir)
        if not pretend and not bad(zodb):
            e = os.system('rsync -av %s %s'%(zodb, donedir))
            if not e:
                os.unlink(zodb)
    except Exception, e:
        error('%s', traceback.format_exc())
        time.sleep(5)
