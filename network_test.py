#!/usr/bin/python

from unittest import TestCase
from logging import critical
import random
import sys
import os

import test_common
from test_common import *
from network import Network, TOPOLOGIES
from node import SigmoidNode, BeerNode, WallenNode, LogicalNode, SineNode
from plot import plotNetwork

random.seed()

class NetworkTest:

    fprefix = 'test/network_'
    nodea = {}

    def dot(self, n, name):
        name = self.fprefix + name
        plotNetwork(n, name+'.dot')
        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
        if test_common.interactive:
            os.popen('kghostview %s.ps'%name)

    def do(self, n, i, o, top, update):
        net = Network(n, i, o, self.nodet, self.nodea, top, update)
        ns = str(self.nodet)
        nc = ns[ns.find('.')+1:ns.rfind('\'')]
        s = '%s_%s'%(nc, top)
        self.dot(net, s)

    def test_01_1d(self):
        self.do(4,1,1, '1d', 'async')

    def test_02_2d(self):
        self.do(9,0,0, '2d', 'async')

    def test_03_full(self):
        self.do(4,0,0, 'full', 'async')

    def test_04_2d_with_3i2o(self):
        self.do(9,3,2, '2d', 'async')

    def test_06_run_net_with_all_topologies(self):
        for topology in TOPOLOGIES:
            net = Network(9,3,2, self.nodet, self.nodea, topology, 'sync')
            net.reset()
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

class Sigmoid(NetworkTest,TestCase):
    nodet = SigmoidNode
class Beer(NetworkTest,TestCase):
    nodet = BeerNode
class Sine(NetworkTest,TestCase):
    nodet = SineNode
class Wallen(NetworkTest,TestCase):
    nodet = WallenNode
class Logical(NetworkTest,TestCase):
    nodet = LogicalNode
    nodea = {'numberOfStates':2}

if __name__ == "__main__":
    test_main()
