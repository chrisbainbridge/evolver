#!/usr/bin/python

import unittest
import logging
import random
import sys
import os
import testoob

from persistent.list import PersistentList
from cgkit.cgtypes import vec3
import test_common
from test_common import *
from network import Network, TOPOLOGIES
import node
from plot import plotNetwork

class NetworkTestCase(unittest.TestCase):

    def setUp(self):
        random.seed()
        self.fprefix = 'test/network_'
    
    def dot(self, n, name):
        name = self.fprefix + name
        plotNetwork(n, name+'.dot')
        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
        if test_common.interactive:
            os.popen('kghostview %s.ps'%name)

    def test_01_sigmoid_1d(self):
        n = Network(4,1,1, node.SigmoidNode, {}, '1d', 'async')
        self.dot(n, 'sigmoid_1d')

    def test_02_sigmoid_2d(self):
        net = Network(9,0,0, node.SigmoidNode, {}, '2d', 'async')
        self.dot(net, 'sigmoid_2d')

    def test_03_sigmoid_full(self):
        net = Network(4,0,0, node.SigmoidNode, {}, 'full', 'async')
        self.dot(net, 'sigmoid_full')

    def test_04_sigmoid_2d_with_3i2o(self):
        n = Network(9,3,2, node.SigmoidNode, {}, '2d', 'async')
        self.dot(n, 'sigmoid_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

    def test_05_init_logical_net(self):
        n = Network(9,3,2, node.LogicalNode, {'numberOfStates':2}, '2d', 'sync')
        self.dot(n, 'logical_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

    def test_06_run_sigmoid_net_with_all_topologies(self):
        for topology in TOPOLOGIES:
            net = Network(9,3,2, node.SigmoidNode, {}, topology, 'sync')
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

    def test_07_run_logical_net_with_all_topologies(self):
        for topology in TOPOLOGIES:
            net = Network(9,3,2, node.LogicalNode, {'numberOfStates':2}, topology, 'sync')
            for n in net:
                n.randomiseState()
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

if __name__ == "__main__":
    test_main()
