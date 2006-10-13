#!/usr/bin/python

import unittest
import logging
import sys
import testoob
import new

import ev
from test_common import *

rl = logging.getLogger()

POPS = ['ev_test_sigmoid', 'ev_test_sigmoid_quantised', 'ev_test_logical']

SECONDS = 20
DEFAULT_CREATE_ARGS = '-p 3 -t %d -g 5' \
                    ' --topology 1d --update async' \
                    ' --nodes 10' \
                    ' --sim bpg --fitness mean-distance '%SECONDS
CREATE_ARGS = {
        'ev_test_sigmoid' : DEFAULT_CREATE_ARGS + '--node_type sigmoid', 
        'ev_test_sigmoid_quantised' : DEFAULT_CREATE_ARGS + '--node_type sigmoid -q 32',
        'ev_test_logical' : DEFAULT_CREATE_ARGS + '--node_type logical --states 2'
        }

def getCreateArgs(popName):
    return ('ev.py -r %s %s'%(popName, CREATE_ARGS[popName]))

class EvTestCase(unittest.TestCase):
    pass

def createFunc(name, args):
    def func(self):
        sys.argv = args.split()
        ev.main()
    m = new.instancemethod(func, None, EvTestCase)
    setattr(EvTestCase, name, m)

x = 0
def getName(op):
    global x
    s = 'test_%d_%s_%s'%(x, op, pop)
    x += 1
    return s

for pop in POPS:
    createFunc(getName('delete'), 'ev.py -r %s -e'%pop)
    createFunc(getName('create'), getCreateArgs(pop))
    createFunc(getName('run'), 'ev.py -r %s -c -m'%pop)

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
