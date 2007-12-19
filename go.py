#!/usr/bin/python

import db, transaction, random, logging, os, sys, time, traceback
import time, popen2, re, copy
from logging import debug, error
from ZODB.FileStorage import FileStorage
from ConfigParser import SafeConfigParser

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('ZEO').setLevel(logging.INFO)
config = SafeConfigParser()
config.read(os.path.expanduser('~/.ev'))
donedir = config.get('cluster','donedir')
if donedir[-1] != '/':
    donedir += '/'
pretend = 0
if '-p' in sys.argv:
    pretend = 1

while 1:
    try:
        debug('ls done')
        o,i = popen2.popen2('rsync %s'%donedir)
        files = [x.split(' ')[-1][:-1] for x in o.readlines()]
        done = [x for x in files if re.match(r'[pb]\d\d\d$', x)]
        debug('db.connect')
        root = db.connect()
        r = [x for x in root['runs'] if x not in done]
        if not r:
            debug('all done')
            break
        # fixme: resume - we should check in /var/tmp/%s for root['runs'] run
        # names. if found and exists in ~/done: erase it, else resume it.
        # note this strategy is suboptimal - would be better to use timestamps
        # and just choose and update the oldest one
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
        debug('eval %s', zodb)
        if not pretend:
            e = os.system('ev -f %s -c -m'%(zodb))
            if e:
                error('child process failed')
                continue
        debug('pack %s', zodb)
        if not pretend:
            FileStorage(zodb).pack(time.time(), None)
        debug('rsync %s %s', zodb, donedir)
        if not pretend:
            os.system('rsync -av %s %s'%(zodb, donedir))
    except Exception, e:
        error('%s', traceback.format_exc())
        time.sleep(5)
