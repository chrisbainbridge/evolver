#!/usr/bin/python

from unittest import TestCase
import sys
import testoob

import ev
from test_common import test_main
from logging import debug, info, critical

STDARGS = '-p 3 -t 3 -g 3 --top 1d --timing async --neurons 5'

def main(s):
    sys.argv = s.split()
    ev.main()

def delete(g):
    main('ev.py -f test.db -r %s -e'%g)

def create(g, args):
    main('ev.py -f test.db -r %s %s'%(g, args))

def run(g):
    main('ev.py -f test.db -r %s -c -m'%g)

def plot(g):
    debug('testing --pf')
    main('ev.py -f test.db -r %s --pf test/%s-fitness.pdf'%(g, g))
    debug('testing --plotpi')
    main('ev.py -f test.db -r %s --plotpi test/%s-childpi.pdf'%(g, g))
    debug('testing --plotfc')
    main('ev.py -f test.db -r %s --plotfc test/%s-childfc.pdf'%(g, g))

class EvTest:
    def test_1_create(self):
        delete(self.name)
        create(self.name, STDARGS + ' ' + self.args)
    def test_2_run(self):
        run(self.name)
    def test_3_plot(self):
        plot(self.name)
    def test_4_erase(self):
        delete(self.name)

class Sigmoid(EvTest, TestCase):
    name = 'ev_sigmoid'
    args = '--model sigmoid'
class Beer(EvTest, TestCase):
    name = 'ev_beer'
    args = '--model beer'
class SigmoidQuanta(EvTest, TestCase):
    name = 'ev_sigmoid_q'
    args = '--model sigmoid -q 32'
class SteadyState(EvTest, TestCase):
    name = 'ev_steadystate'
    args = '--model sigmoid --ga steadystate'
class Logical(EvTest, TestCase):
    name = 'ev_logical'
    args = '--model logical -q 2'
class Pb(EvTest, TestCase):
    name = 'ev_pb'
    args = '--sim pb'


if __name__ == "__main__":
    test_main()
