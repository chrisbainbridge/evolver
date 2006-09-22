#!/usr/bin/python

import unittest
import logging
import random
import time
import sys
import os
import testoob

from persistent.list import PersistentList
from cgkit.cgtypes import vec3

import network
import node

rl = logging.getLogger()

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
        os.popen('kghostview %s.ps'%name)

    def test_01_sigmoid_1d(self):
        n = network.Network(4,0,0, node.SigmoidNode, {}, '1d', 'async')
        self.dot(n, '01_sigmoid_1d')

    def test_02_sigmoid_2d(self):
        net = network.Network(9,0,0, node.SigmoidNode, {}, '2d', 'async')
        self.dot(net, '02_sigmoid_2d')

    def test_03_sigmoid_full(self):
        net = network.Network(4,0,0, node.SigmoidNode, {}, 'full', 'async')
        self.dot(net, '03_sigmoid_full')

#    def test_03_sigmoid_3d(self):
#        n = network.Network(20,0,0, node.Sigmoid, {}, '3d', 'async')
#        self.dot(n, '03_sigmoid_3d')

    def test_04_sigmoid_2d_with_3i2o(self):
        n = network.Network(9,3,2, node.SigmoidNode, {}, '2d', 'async')
        self.dot(n, '04_sigmoid_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

    def test_05_init_multi_value_net(self):
        n = network.Network(9,3,2, node.Logical, {}, '2d', 'sync')
        self.dot(n, '05_sigmoid_2d_with_3i2o')
        assert len(n.inputs) == 3
        assert len(n.outputs) == 2

#    def test_02_init_mvlf(self):
#        network.Network(20,0,0, lambda : node.MultiValueLogical())
#
#    def test_03_init_logical(self):
#        network.Network(20,0,0, lambda : node.Logical())
#
#    def test_05_init_mvlf_io(self):
#        network.Network(20,4,3, lambda : node.MultiValueLogical())
#
#    def test_06_init_logical_io(self):
#        network.Network(20,4,3, lambda : node.Logical())
#
#
#    def test_10_connect_randomk(self):
#        n = network.Network(20,4,3, lambda : node.Sigmoid(), 'randomk')
#        self.dot(n, '10_connect_randomk')
#
#    def test_11_connect_full(self):
#        n = network.Network(20,4,3, lambda : node.Sigmoid(), 'full')
#        self.dot(n, '11_connect_full')

if __name__ == "__main__":
    setup_logging()
    testoob.main()
