#!/usr/bin/python

from unittest import TestCase
import logging
import sys
import testoob

import ev
from test_common import *

rl = logging.getLogger()

DEFAULT_CREATE_ARGS = '-p 3 -t 3 -g 3' \
                    ' --topology 1d --update async' \
                    ' --nodes 10' \
                    ' --sim bpg --fitness mean-distance '

def main(s):
    sys.argv = s.split()
    ev.main()

def delete(g):
    main('ev.py -r %s -e'%g)

def create(g, args):
    main('ev.py -r %s %s %s'%(g, DEFAULT_CREATE_ARGS, args))

def run(g):
    main('ev.py -r %s -c -m'%g)

def plot(g):
    main('ev.py -r %s --plotfitness test/%s-fitness.pdf'%(g, g))
    main('ev.py -r %s --plotchildpi test/%s-childpi.pdf'%(g, g))
    main('ev.py -r %s --plotchildfc test/%s-childfc.pdf'%(g, g))

class TestLogical(TestCase):
    g = 'test_logical'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--node_type logical --states 2')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

class TestSigmoid(TestCase):
    g = 'test_sigmoid'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--node_type sigmoid')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)
        
class TestSigmoidQuantised(TestCase):
    g = 'test_sigmoid_q'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--node_type sigmoid -q 32')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

class TestSteadyState(TestCase):
    g = 'test_steadystate'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--node_type sigmoid --ga-steady-state')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

if __name__ == "__main__":
    setup_logging(rl)
    logging.getLogger('ZEO').setLevel(logging.WARNING)
    testoob.main()
