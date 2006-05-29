# -*- Mode: Python; tab-width: 4 -*-

import sys
import types

from persistent import Persistent

def get_refcounts():
    d = {}
    #sys.modules
    # collect all classes
    for m in sys.modules.values():
        for sym in dir(m):
            o = getattr (m, sym)
            if type(o) is types.ClassType or type(o) is types.TypeType:
            #if hasattr(o, '__class__'):
                #issubclass(o, Persistent):
                d[o] = sys.getrefcount (o)
    # sort by refcount
    pairs = map (lambda x: (x[1],x[0]), d.items())
    pairs.sort()
    pairs.reverse()
    return pairs

def print_top_100():
    for n, c in get_refcounts()[:100]:
        print '%10d %s' % (n, c.__name__)

if __name__ == '__main__':
    top_100()
