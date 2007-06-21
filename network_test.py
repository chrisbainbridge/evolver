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

class NetworkTest(TestCase):

    def setUp(self):
        random.seed()
        self.fprefix = 'test/network_'

    def dot(self, n, name):
        name = self.fprefix + name
        plotNetwork(n, name+'.dot')
        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
        if test_common.interactive:
            os.popen('kghostview %s.ps'%name)

    def do(self, n, i, o, top, update):
        net = Network(n, i, o, nodet, nodea, top, update)
        ns = str(nodet)
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
            net = Network(9,3,2, nodet, nodea, topology, 'sync')
            net.reset()
            for n in net:
                n.preUpdate()
            for n in net:
                n.postUpdate()

if __name__ == "__main__":
    opts = {'--sigmoid' : (SigmoidNode, {}),
            '--beer' :    (BeerNode, {}),
            '--sine' :    (SineNode, {}),
            '--wallen' :    (WallenNode, {}),
            '--logical' : (LogicalNode, {'numberOfStates':2})}
    nodet = None
    for a in opts:
        if a in sys.argv:
            sys.argv.remove(a)
            nodet = opts[a][0]
            nodea = opts[a][1]
    if nodet:
        test_main()
    else:
        for nodet in opts:
            cmd = '%s %s %s'%(sys.argv[0], nodet, ' '.join(sys.argv[1:]))
            critical(cmd)
            os.system(cmd)
