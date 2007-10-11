#!/usr/bin/python

from unittest import TestCase
from logging import critical
import random
import sys
import os
import re
import math
from Cheetah.Template import Template

import test_common
from test_common import *
from network import Network, TOPOLOGIES
from node import SigmoidNode, BeerNode, TagaNode, WallenNode, LogicalNode, SineNode
from plot import plotNetwork

random.seed()

class NodeTest:

    def openf(self):
        ns = re.search(r'\.(\w+)',str(self.nodet)).group(1)
        i = ''
        if self.nodet == WallenNode:
            i = '%d'%self.i
        self.prefix = 'test/%s%s-q%02d'%(ns,i, self.quanta)
        self.f = open('%s.txt'%self.prefix, 'w')
        self.f.write('time output stimulus\n')

    def plot(self):
        t = Template(file='plot_node.r')
        t.base = self.prefix
        self.f = open('tmp.r', 'w')
        self.f.write(t.respond())
        self.f.close()
        os.system('R -q --no-save < tmp.r >> r.out 2>&1')

    def runsim(self):
        self.openf()

        n0 = self.nodet(quanta=self.quanta)
        n1 = self.nodet(quanta=self.quanta)
        n0.addInput(n1)
        n0.weights[n1] = 2
        if self.nodet == SigmoidNode:
            n0.weights[n1] = 2
        elif self.nodet == SineNode:
            n0.amplitude = 1.0
            n0.stepSize = math.pi*2/50
        elif self.nodet == BeerNode:
            n0.weights[n1] = 4
            n0.bias = 0
            n0.adaptRate = 0.05
            n0.state = 0
        elif self.nodet == TagaNode:
            n0.weights[n1] = 2
        elif self.nodet == WallenNode:
            n0.weights[n1] = 2
            n0.i = self.i
            n0.yt = 0
            n0.ye = 0
            n0.yi = 0
            if n0.i == 3:
                n0.weights[n1] = 15.0
        n0.output = 0

        stim = {0:0, 500:0.3, 1000:0.6, 2000:1.0, 3000:0.5, 4000:0.0}
        i = 0
        # stimulus initially inhibits
        if self.nodet == WallenNode:
            n1.excite = 0
        else:
            n0.weights[n1] = -n0.weights[n1]
        while i < 5000:
            # stimulus goes excitatory after delay
            if i == 1500:
                if self.nodet == WallenNode:
                    n1.excite = 1
                else:
                    n0.weights[n1] = -n0.weights[n1]
            n1.output = stim[max([k for k in stim if k<=i])]
            n0.preUpdate()
            n0.postUpdate()
            s = '%f %f %f\n'%(i/1000.0, n0.output, n1.output)
            self.f.write(s)
            i += 20

        self.plot()

    def test_q0(self):
        self.quanta = 0
        self.runsim()
    def test_q2(self):
        self.quanta = 2
        self.runsim()
    def test_q4(self):
        self.quanta = 4
        self.runsim()
    def test_q8(self):
        self.quanta = 8
        self.runsim()
    def test_q16(self):
        self.quanta = 16
        self.runsim()
    def test_q32(self):
        self.quanta = 32
        self.runsim()
    def test_q64(self):
        self.quanta = 64
        self.runsim()

class Sigmoid(NodeTest,TestCase):
    nodet = SigmoidNode
class Sine(NodeTest,TestCase):
    nodet = SineNode
class Beer(NodeTest,TestCase):
    nodet = BeerNode
class Taga(NodeTest,TestCase):
    nodet = TagaNode
class Wallen0(NodeTest,TestCase):
    nodet = WallenNode
    i = 0
class Wallen1(NodeTest,TestCase):
    nodet = WallenNode
    i = 1
class Wallen2(NodeTest,TestCase):
    nodet = WallenNode
    i = 2
class Wallen3(NodeTest,TestCase):
    nodet = WallenNode
    i = 3
#class Logical(NetworkTest,TestCase):
#    nodet = LogicalNode
#    nodea = {'numberOfStates':2}

if __name__ == "__main__":
    test_main()
