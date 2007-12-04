#!/usr/bin/python

from unittest import TestCase
from logging import critical
import sys
import os
from math import sqrt, floor
import random

import test_common
from test_common import *
from network import Network, TOPOLOGIES
from node import SigmoidNode, BeerNode, EkebergNode, LogicalNode, SineNode, IfNode, SrmNode
from plot import plotNetwork

random.seed(0)

class NetworkTest:

    fprefix = 'test/network_'
    nodea = {}

    def dot(self, n, name):
        name = self.fprefix + name
        plotNetwork(n, name+'.dot')
        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
        if test_common.interactive:
            os.popen('kghostview %s.ps'%name)

    def do(self, n, i, o, top, update, r, u):
        net = Network(n, i, o, self.nodet, self.nodea, top, update, r, u)
        net.mutate(1)
        ns = str(self.nodet)
        nc = ns[ns.find('.')+1:ns.rfind('\'')]
        s = '%s_%s'%(nc, top)
        self.dot(net, s)

    def test_01_1d(self):
        self.do(4,1,1, '1d', 'async', 1, 0)

    def test_02_2d(self):
        self.do(9,0,0, '2d', 'async', 1, 0)

    def test_03_full(self):
        self.do(4,0,0, 'full', 'async', 1, 0)

    def test_04_rk(self):
        self.do(9,3,2, 'rk', 'async', 1, 0)

    def test_05_2d_with_3i2o(self):
        self.do(9,3,2, '2d', 'async', 1, 0)

    def test_06_run_net_with_all_topologies(self):
        for topology in TOPOLOGIES:
            maxr = 3
            num_nodes = 16
            # 2d topology doesn't allow overlap of neighbourhood
            if topology == '2d' and sqrt(num_nodes) < maxr*2+1:
                maxr = floor((sqrt(num_nodes)-1)/2)
            radius = random.randint(1,maxr)
            uniform = random.randint(0,1)
            net = Network(num_nodes,3,2, self.nodet, self.nodea, topology, 'sync', radius, uniform)
            net.reset()
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

    def test_07_uniform(self):
        self.do(4,0,0, 'full', 'async', 1, 1)

class Sigmoid(NetworkTest,TestCase):
    nodet = SigmoidNode
class Beer(NetworkTest,TestCase):
    nodet = BeerNode
class Sine(NetworkTest,TestCase):
    nodet = SineNode
class Ekeberg(NetworkTest,TestCase):
    nodet = EkebergNode
class If(NetworkTest,TestCase):
    nodet = IfNode
class Srm(NetworkTest,TestCase):
    nodet = SrmNode
class Logical(NetworkTest,TestCase):
    nodet = LogicalNode
    nodea = {'quanta':2}

if __name__ == "__main__":
    test_main()
