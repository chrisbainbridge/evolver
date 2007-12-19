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
donedir = config.get('cluster','donedir')
if donedir[-1] != '/':
    donedir += '/'
pat = r'[pb]\d\d\d$'
pretend = 0
if '-p' in sys.argv:
    pretend = 1

def lsdone():
    o,i = popen2.popen2('rsync %s'%donedir)
    files = [x.split(' ')[-1][:-1] for x in o.readlines()]
    done = [x for x in files if re.match(pat, x)]
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
        oldruns = [x for x in os.listdir('/var/tmp/') if re.match(pat,x) and os.stat('/var/tmp/%s'%x).st_mtime < time.time()-5*60]
        debug('oldruns %s', oldruns)
        for x in oldruns[:]:
            if busy('/var/tmp/%s'%x):
                debug('/var/tmp/%s is busy',x)
                oldruns.remove(x)
            elif x in done or bad(x):
                debug('rm oldrun /var/tmp/%s'%x)
                if not pretend:
                    os.unlink('/var/tmp/%s'%x)
                oldruns.remove(x)
        # oldruns now contains potentially valid runs
        if oldruns:
            debug('valid oldruns %s', oldruns)
            zodb = '/var/tmp/%s'%random.choice(oldruns)
        else:
            debug('db.connect')
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
            zodb = '/var/tmp/%s'%c.name
            debug('create %s', zodb)
            if os.path.exists(zodb):
                os.unlink(zodb)
            if not pretend:
                e = os.system('%s -f %s'%(c.cl, zodb))
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
