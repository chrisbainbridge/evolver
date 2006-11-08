#!/usr/bin/python

from unittest import TestCase
import logging
import sys
import testoob
import new

import ev
from test_common import *

rl = logging.getLogger()

SECONDS = 20
DEFAULT_CREATE_ARGS = '-p 3 -t %d -g 3' \
                    ' --topology 1d --update async' \
                    ' --nodes 10' \
                    ' --sim bpg --fitness mean-distance '%SECONDS

def main(s):
    sys.argv = s.split()
    ev.main()

def delete(gen):
    main('ev.py -r %s -e'%gen)

def create(gen, args):
    main('ev.py -r %s %s %s'%(gen, DEFAULT_CREATE_ARGS, args))

def run(gen):
    main('ev.py -r %s -c -m'%gen)

class TestSigmoid(TestCase):
    def test_1_delete(self):
        delete('test_sigmoid')
    def test_2_create(self):
        create('test_sigmoid', '--node_type sigmoid')
    def test_3_run(self):
        run('test_sigmoid')
        
class TestSigmoidQuantised(TestCase):
    def test_1_delete(self):
        delete('test_sigmoid_q')
    def test_2_create(self):
        create('test_sigmoid_q', '--node_type sigmoid -q 32')
    def test_3_run(self):
        run('test_sigmoid_q')

class TestLogical(TestCase):
    def test_1_delete(self):
        delete('test_logical')
    def test_2_create(self):
        create('test_logical', '--node_type logical --states 2')
    def test_3_run(self):
        run('test_logical')

class TestSteadyState(TestCase):
    def test_1_delete(self):
        delete('test_steadystate')
    def test_2_create(self):
        create('test_steadystate', '--node_type sigmoid --ga-steady-state')
    def test_3_run(self):
        run('test_steadystate')

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
