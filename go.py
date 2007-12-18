#!/usr/bin/python

import db, transaction, random, logging, os, sys, time, traceback
from logging import debug, error
from ZODB.FileStorage import FileStorage
import time

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('ZEO').setLevel(logging.INFO)
D = os.path.expanduser('~/done')

while 1:
    try:
        debug('db.connect')
        root = db.connect()
        r = [x for x in root['runs'] if not os.path.exists('%s/%s'%(D,x.name))]
        if not r:
            debug('all done')
            break
        # note this strategy is suboptimal - would be better to use timestamps
        # and just choose and update the oldest one
        m = min([x.taken for x in r])
        l = [x for x in r if x.taken == m]
        c = random.choice(l)
        c.taken += 1
        transaction.commit()
        debug('db.close')
        db.close()
        debug('run %s', c.name)
        zodb = '/var/tmp/%s'%c.name
        debug('create %s', zodb)
        if os.path.exists(zodb):
            os.unlink(zodb)
        e = os.system('%s -f %s'%(c.cl, zodb))
        if e:
            error('child process failed')
            continue
        debug('eval %s', zodb)
        e = os.system('ev -f %s -c -m'%(zodb))
        if e:
            error('child process failed')
            continue
        debug('pack %s', zodb)
        FileStorage(zodb).pack(time.time(), None)
        debug('mv %s %s', zodb, D)
        os.system('cp --remove-destination %s %s'%(zodb, D))
    except Exception, e:
        error('%s', traceback.format_exc())
        time.sleep(5)
