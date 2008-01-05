#!/usr/bin/python

import socket, sys, time, os, re
from ZODB.FileStorage import FileStorage

pat = r'[pb]\d\d\d$'
tmp = os.path.expanduser('~/tmp/%s/'%socket.gethostname())
oldruns = [x for x in os.listdir(tmp) if re.match(pat,x)]
for zodb in oldruns:
    print 'packing',zodb
    FileStorage(tmp+zodb).pack(time.time(), None)
    os.unlink(tmp+zodb+'.old')
