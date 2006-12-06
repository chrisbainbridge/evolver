#!/usr/bin/python

from unittest import TestCase
import logging
import sys
import testoob

import ev
from test_common import *
from logging import debug

ARG_T = '-p 3 -t 3 -g 3 --topology 1d --update async --nodes 10  %s '
DEFAULT_CREATE_ARGS = ARG_T%('--sim bpg --fitness mean-distance')
suffix = ''

def main(s):
    sys.argv = s.split()
    ev.main()

def delete(g):
    g += suffix
    main('ev.py -r %s -e'%g)

def create(g, args):
    g += suffix
    main('ev.py -r %s %s %s'%(g, DEFAULT_CREATE_ARGS, args))

def run(g):
    g += suffix
    main('ev.py -r %s -c -m'%g)

def plot(g):
    g += suffix
    debug('testing --plotfitness')
    main('ev.py -r %s --plotfitness test/%s-fitness.pdf'%(g, g))
    debug('testing --plotpi')
    main('ev.py -r %s --plotpi test/%s-childpi.pdf'%(g, g))
    debug('testing --plotfc')
    main('ev.py -r %s --plotfc test/%s-childfc.pdf'%(g, g))

class TestLogical(TestCase):
    g = 'test_logical'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--nodetype logical --states 2')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

class TestSigmoid(TestCase):
    g = 'test_sigmoid'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--nodetype sigmoid')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)
        
class TestSigmoidQuantised(TestCase):
    g = 'test_sigmoid_q'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--nodetype sigmoid -q 32')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

class TestSteadyState(TestCase):
    g = 'test_steadystate'
    def test_1_delete(self):
        delete(self.g)
    def test_2_create(self):
        create(self.g, '--nodetype sigmoid --steadystate')
    def test_3_run(self):
        run(self.g)
    def test_4_plot(self):
        plot(self.g)

if __name__ == "__main__":
    if '--pb' in sys.argv:
        DEFAULT_CREATE_ARGS = ARG_T%('--sim pb')
        sys.argv.remove('--pb')
        suffix = '-pb'
    test_main()
