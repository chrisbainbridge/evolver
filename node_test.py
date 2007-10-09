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
from node import SigmoidNode, BeerNode, TagaNode, WallenNode, LogicalNode, SineNode
from plot import plotNetwork

random.seed()

class NodeTest:

    def test_01(self):
        ns = re.search(r'\.(\w+)',str(self.nodet)).group(1)
        i = ''
        if self.nodet == WallenNode:
            i = '%d'%self.i
        prefix = 'test/%s%s'%(ns,i)
        f = open('%s.txt'%prefix, 'w')
        f.write('time output stimulus\n')
        n0 = self.nodet()
        n1 = self.nodet()
        n0.addInput(n1)
        n0.weights[n1] = 2
        if self.nodet == BeerNode:
            n0.weights[n1] = 2
            n0.bias = 0
            n0.adaptRate = 1
            n0.state = 0
        elif self.nodet == TagaNode:
            n0.weights[n1] = 1
            n0.tau0 = 0.2
        elif self.nodet == WallenNode:
            n0.weights[n1] = 2
            n0.i = self.i
            n0.yt = 0
            n0.ye = 0
            n0.yi = 0
            n1.excite = 1
        n0.output = 0
        stim = {0:0, 500:0.3, 1000:0.6, 2000:1.0, 3000:0.5, 4000:0.0}
        i = 0
        while i < 5000:
            n1.output = stim[max([k for k in stim if k<=i])]
            n0.preUpdate()
            n0.postUpdate()
            s = '%f %f %f\n'%(i/1000.0, n0.output, n1.output)
            f.write(s)
            i += 20
        t = Template(file='plot_node.r')
        t.base = prefix
        f = open('tmp.r', 'w')
        f.write(t.respond())
        f.close()
        os.system('R -q --no-save < tmp.r >> r.out 2>&1')

class Sigmoid(NodeTest,TestCase):
    nodet = SigmoidNode
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
