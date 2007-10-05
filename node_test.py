#!/usr/bin/python

from unittest import TestCase
from logging import critical
import random
import sys
import os
import re
from Cheetah.Template import Template

import test_common
from test_common import *
from network import Network, TOPOLOGIES
from node import SigmoidNode, BeerNode, WallenNode, LogicalNode, SineNode
from plot import plotNetwork

random.seed()
#import pdb

class NodeTest:

#    fprefix = 'test'
#    nodea = {}

#    def dot(self, n, name):
#        name = self.fprefix + name
#        plotNetwork(n, name+'.dot')
#        os.popen('dot -Tps -o %s.ps %s.dot'%(name,name))
#        if test_common.interactive:
#            os.popen('kghostview %s.ps'%name)

#    def do(self, n, i, o, top, update):

    def test_01(self):
        ns = re.search(r'\.(\w+)',str(self.nodet)).group(1)
        f = open('test/%s.txt'%ns, 'w')
        f.write('time output stimulus\n')
        n0 = self.nodet()
        n1 = self.nodet()
        n0.addInput(n1)
        n0.weights[n1] = 2
        n0.output = 0
        stim = {0:0.3, 1000:0.6, 2000:1.0, 3000:0.5, 4000:0.0}
        i = 0
        while i < 5000:
            x = [k for k,v in stim.items() if k<=i][-1]
            n1.output = stim[x]
            n0.preUpdate()
            n0.postUpdate()
#            pdb.set_trace()
            s = '%f %f %f\n'%(i/1000.0, n0.output, n1.output)
            f.write(s)
            i += 20
        t = Template(file='plot_node.r')
        t.base = 'test/%s'%ns
        f = open('tmp.r', 'w')
        f.write(t.respond())
        f.close()
        os.system('R -q --no-save < tmp.r >> r.out 2>&1')

#        net = Network(n, i, o, self.nodet, self.nodea, top, update)
#        ns = str(self.nodet)
#        nc = ns[ns.find('.')+1:ns.rfind('\'')]
#        s = '%s_%s'%(nc, top)
#        self.dot(net, s)

#    def test_01_1d(self):
#        self.do(4,1,1, '1d', 'async')

#    def test_02_2d(self):
#        self.do(9,0,0, '2d', 'async')

#    def test_03_full(self):
#        self.do(4,0,0, 'full', 'async')

#    def test_04_2d_with_3i2o(self):
#        self.do(9,3,2, '2d', 'async')

#    def test_06_run_net_with_all_topologies(self):
#        for topology in TOPOLOGIES:
#            net = Network(9,3,2, self.nodet, self.nodea, topology, 'sync')
#            net.reset()
#            for n in net:
#                n.preUpdate()
#            for n in net:
#                n.postUpdate()

class Sigmoid(NodeTest,TestCase):
    nodet = SigmoidNode
#class Beer(NetworkTest,TestCase):
#    nodet = BeerNode
#class Sine(NetworkTest,TestCase):
#    nodet = SineNode
#class Wallen(NetworkTest,TestCase):
#    nodet = WallenNode
#class Logical(NetworkTest,TestCase):
#    nodet = LogicalNode
#    nodea = {'numberOfStates':2}

if __name__ == "__main__":
    test_main()
