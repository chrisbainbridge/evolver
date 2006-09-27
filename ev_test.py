#!/usr/bin/python

import unittest
import logging
import sys
import testoob

import ev
from test_common import *

rl = logging.getLogger()

POPS = ['ev_test_sigmoid', 'ev_test_sigmoid_quantised', 'ev_test_logical']
SECONDS = 20

class EvTestCase(unittest.TestCase):

    def test_0_deletepops(self):
        for pop in POPS:
            sys.argv = ('ev.py -r %s -e'%pop).split()
            ev.main()

    def test_1_createpop_sigmoid(self):
        sys.argv = ('ev.py -r ev_test_sigmoid -p 3 -t %d -g 5' \
                    ' --topology 1d --update async' \
                    ' --node_type sigmoid --nodes 10' \
                    ' --sim bpg'%SECONDS).split()
        ev.main()
        
    def test_2_createpop_sigmoid_quantised(self):
        sys.argv = ('ev.py -r ev_test_sigmoid_quantised -p 3 -t %d -g 5' \
                    ' --topology 1d --update async' \
                    ' --node_type sigmoid --nodes 10' \
                    ' --sim bpg -q 32'%SECONDS).split()
        ev.main()
        
    def test_3_createpop_logical(self):
        sys.argv = ('ev.py -r ev_test_logical -p 3 -t %d -g 5' \
                    ' --topology 1d --update async' \
                    ' --node_type logical --states 2 --nodes 10' \
                    ' --sim bpg'%SECONDS).split()
        ev.main()

    def test_4_evolvepops(self):
        for pop in POPS:
            sys.argv = ('ev.py -r %s -c -m'%pop).split()
            ev.main()

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
