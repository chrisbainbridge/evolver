#!/usr/bin/python

import unittest
import logging
import sys
import testoob

import ev
from test_common import *

rl = logging.getLogger()

class main(unittest.TestCase):

    def test_0_createpop(self):
        sys.argv = 'ev.py -r ev_test -e'.split()
        ev.main()
        sys.argv = 'ev.py -r ev_test -p 3 -t 15 -g 2' \
                    ' --topology 1d --update async' \
                    ' --node_type Sigmoid --nodes 10' \
                    ' --simulation bpg'.split()
        ev.main()

    def test_1_evolvepop(self):
        sys.argv = 'ev.py -r ev_test -c -m'.split()
        ev.main()

    def test_2_deletepop(self):
        sys.argv = 'ev.py -r ev_test -e'.split()
        ev.main()

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
