#!/usr/bin/python

import sys
import random
import logging
logging.basicConfig()

import ZODB
from ZODB.config import storageFromString
from ZEO.cache import Entry

from BTrees.OOBTree import OOBTree
import transaction


config = """\
   <zeoclient>
   server localhost:12345
   cache-size 100KB

   </zeoclient>
"""
#    client glimmer
st = storageFromString(config)
db = ZODB.DB(st)
cn = db.open()
rt = cn.root()

if "tree" not in rt:
   rt["tree"] = OOBTree()
   transaction.commit()
tree = rt["tree"]

logging.getLogger().critical('hw')

N = 1000
for i in xrange(N):
   j = random.randrange(1000000000)
   tree[j] = str(j)
   transaction.commit()
   print sys.getrefcount(Entry),
   logging.getLogger().critical('%d', sys.getrefcount(Entry))
print
db.close()
