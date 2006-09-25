#!/usr/bin/python

import unittest
import logging
import sys
import testoob

import ev
from test_common import *

rl = logging.getLogger()

POPS = ['ev_test_sigmoid', 'ev_test_logical']

class EvTestCase(unittest.TestCase):

    def test_0_deletepops(self):
        for pop in POPS:
            sys.argv = ('ev.py -r %s -e'%pop).split()
            ev.main()

    def test_1_createpop_sigmoid(self):
        sys.argv = ('ev.py -r %s -p 3 -t 1 -g 5' \
                    ' --topology 1d --update async' \
                    ' --node_type sigmoid --nodes 10' \
                    ' --sim bpg'%POPS[0]).split()
        ev.main()
        
    def test_2_createpop_logical(self):
        sys.argv = ('ev.py -r %s -p 3 -t 1 -g 5' \
                    ' --topology 1d --update async' \
                    ' --node_type logical --states 2 --nodes 10' \
                    ' --sim bpg'%POPS[1]).split()
        ev.main()

    def test_3_evolvepops(self):
        for pop in POPS:
            sys.argv = ('ev.py -r %s -c -m'%pop).split()
            ev.main()

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
