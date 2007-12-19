#!/usr/bin/python

import os, sys, re, copy, logging, traceback
from ZODB.FileStorage import FileStorage
from ZODB import DB
from logging import debug, error

logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('ZODB').setLevel(logging.INFO)
D = os.path.expanduser('~/done/')

l = os.listdir(D)
dbs = [(x,D+x) for x in l if re.match(r'[pb]\d\d\d$', x)]
dbs.sort()
for (r,f) in dbs:
    try:
        c = DB(FileStorage(f)).open()
        root = c.root()
        assert len(root[r].scores) == root[r].final_gen_num+1
        if '-d' in sys.argv:
            copy.deepcopy(root[r])
        c.close()
        c.db().close()
        debug('%s OK', r)
    except Exception, e:
        error('%s FAIL\n%s', r, traceback.format_exc())
