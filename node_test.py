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
from node import SigmoidNode, BeerNode, IfNode, SrmNode, TagaNode, EkebergNode, LogicalNode, SineNode, WeightNode
from plot import plotNetwork

class NodeTest:

    def setUp(self):
        random.seed(0)

    def openf(self):
        ns = re.search(r'\.(\w+)Node',str(self.nodet)).group(1)
        i = ''
        if self.nodet == EkebergNode:
            i = '%d'%self.i
        self.prefix = 'test/%s%s-%02d'%(ns, i, self.quanta)
        if self.quanta == 0:
            s = 'continuous'
        else:
            s = '%d state (%d-bit)'%(self.quanta, math.log(self.quanta,2))
        self.title = '%s%s %s'%(ns, i, s)
        self.f = open('%s.txt'%self.prefix, 'w')
        s = 'time output stimulus'
        if self.nodet in [IfNode, SrmNode]:
            s += ' state'
        self.f.write(s+'\n')

    def plot(self):
        t = Template(file='plot_node.r')
        t.base = self.prefix
        t.plot_state = 0
        t.title = self.title
        if self.nodet in [IfNode, SrmNode]:
            t.plot_state = 1
        self.f = open('tmp.r', 'w')
        self.f.write(t.respond())
        self.f.close()
        os.system('R -q --no-save < tmp.r >> r.out 2>&1')

    def runsim(self):
        self.openf()

        kw = {'par' : 1, 'quanta' : self.quanta}
        if self.nodet == LogicalNode:
            kw['numberOfInputs'] = 1
        n0 = self.nodet(**kw)
        n1 = self.nodet(**kw)
        n0.addInput(n1)
        if self.nodet == SigmoidNode:
            n0.weights[n1] = 2
        elif self.nodet == SineNode:
            n0.par.amplitude = 1.0
            n0.par.stepSize = math.pi*2/50
        elif self.nodet in [BeerNode, IfNode]:
            n0.weights[n1] = 4
            n0.par.bias = 0
            n0.par.adaptRate = 0.05
            n0.state = 0
            if self.nodet == IfNode:
                n0.par.bias = 3
                n0.weights[n1] = 5
                n0.par.tr = 25
                n0.par.adaptRate = 0.15
        elif self.nodet == SrmNode:
            n0.weights[n1] = 3.5
            n0.state = 0
            n0.par.ft = 2.0
            n1.par.ft = 2
        elif self.nodet == TagaNode:
            n0.weights[n1] = 2
        elif self.nodet == EkebergNode:
            n0.weights[n1] = 2
            n0.par.i = self.i
            n0.yt = 0
            n0.ye = 0
            n0.yi = 0
            if n0.par.i == 3:
                n0.weights[n1] = 15.0
        n0.output = 0

        stim = {0:0, 500:0.3, 1000:0.6, 2000:1.0, 3000:0.5, 4000:0.0}
        i = 0
        # stimulus initially inhibits
        if self.nodet == EkebergNode:
            n1.par.excite = 0
        elif isinstance(n0, WeightNode):
            n0.weights[n1] = -n0.weights[n1]
        while i < 5000:
            # stimulus goes excitatory after delay
            if i == 1500:
                if self.nodet == EkebergNode:
                    n1.par.excite = 1
                elif isinstance(n0, WeightNode):
                    n0.weights[n1] = -n0.weights[n1]
            if self.nodet == SrmNode:
                p = stim[max([k for k in stim if k<=i])]
                p = 0.6*p
                if random.random() < p:
                    n1.spikes = [0] + n1.spikes
                n1.preUpdate()
                n1.postUpdate()
            n1.output = stim[max([k for k in stim if k<=i])]
            n0.preUpdate()
            n0.postUpdate()
            response = n0.output
            if self.nodet in [IfNode, SrmNode]:
                response *= 0.2
            s = '%f %f %f'%(i/1000.0, response, n1.output)
            if self.nodet in [IfNode, SrmNode]:
                s += ' %f'%(n0.state/8+0.5)
            self.f.write(s+'\n')
            i += 20

        self.plot()

    def test_q0(self):
        if self.nodet == LogicalNode:
            # there's no such thing as a logical node with continuous state
            return
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
class If(NodeTest,TestCase):
    nodet = IfNode
class Srm(NodeTest,TestCase):
    nodet = SrmNode
class Taga(NodeTest,TestCase):
    nodet = TagaNode
class Ekeberg0(NodeTest,TestCase):
    nodet = EkebergNode
    i = 0
class Ekeberg1(NodeTest,TestCase):
    nodet = EkebergNode
    i = 1
class Ekeberg2(NodeTest,TestCase):
    nodet = EkebergNode
    i = 2
class Ekeberg3(NodeTest,TestCase):
    nodet = EkebergNode
    i = 3
class Logical(NodeTest,TestCase):
    nodet = LogicalNode

if __name__ == "__main__":
    test_main()
