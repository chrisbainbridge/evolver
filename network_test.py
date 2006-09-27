#!/usr/bin/python

import unittest
import logging
import random
import sys
import os
import testoob

from persistent.list import PersistentList
from cgkit.cgtypes import vec3

from network import Network
import node

rl = logging.getLogger()
interactive = 0

def setup_logging():
    level = logging.INFO
    if '-d' in sys.argv:
        level = logging.DEBUG
        sys.argv.remove('-d')

    rl.setLevel(level)
    for m in 'neural', 'node':
        l = logging.getLogger(m)
        l.setLevel(level)
    logging.basicConfig()

class NetworkTestCase(unittest.TestCase):

    def setUp(self):
        random.seed()
        self.fprefix = 'test/Network_'
    
    def dot(self, n, name):
        name = self.fprefix + name
        n.plot(name+'.dot')
        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
        if interactive:
            os.popen('kghostview %s.ps'%name)

    def test_01_sigmoid_1d(self):
        n = Network(4,0,0, node.SigmoidNode, {}, '1d', 'async')
        self.dot(n, '01_sigmoid_1d')

    def test_02_sigmoid_2d(self):
        net = Network(9,0,0, node.SigmoidNode, {}, '2d', 'async')
        self.dot(net, '02_sigmoid_2d')

    def test_03_sigmoid_full(self):
        net = Network(4,0,0, node.SigmoidNode, {}, 'full', 'async')
        self.dot(net, '03_sigmoid_full')

    def test_04_sigmoid_2d_with_3i2o(self):
        n = Network(9,3,2, node.SigmoidNode, {}, '2d', 'async')
        self.dot(n, '04_sigmoid_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

    def test_05_init_logical_net(self):
        n = Network(9,3,2, node.LogicalNode, {'numberOfStates':2}, '2d', 'sync')
        self.dot(n, '05_logical_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

    def test_06_run_sigmoid_net_with_all_topologies(self):
        for topology in Network.TOPOLOGIES:
            net = Network(9,3,2, node.SigmoidNode, {}, topology, 'sync')
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

    def test_07_run_logical_net_with_all_topologies(self):
        for topology in Network.TOPOLOGIES:
            net = Network(9,3,2, node.LogicalNode, {'numberOfStates':2}, topology, 'sync')
            for n in net:
                n.randomiseState()
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

if __name__ == "__main__":
    if '-i' in sys.argv:
        interactive = 1
        sys.argv.remove('-i')
    setup_logging()
    testoob.main()
