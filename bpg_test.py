#!/usr/bin/python

import os
import unittest
import random
import pickle
import sys
import testoob

import bpg
import node
import test_common
from test_common import *
from plot import *

class BodyPartTest(unittest.TestCase):
    def test_0_init(self):
        self.bp = bpg.BodyPart(new_network_args)

class BodyPartGraphTest(unittest.TestCase):

    def setUp(self):
        if not os.path.exists('test'):
            os.mkdir('test')
        self.fprefix = 'test/bpg_'

    def tearDown(self):
        pass

    def gv(self, f):
        if test_common.interactive:
            os.system('kpdf %s.pdf'%f)

    def test_1_init(self):
        self.bpg = new_individual_fn(**new_individual_args)
        self.bpg.sanityCheck()

    def test_2_plotBpg(self):
        self.test_1_init()
        fname = self.fprefix + 'plotBpg'
        plotBpg(self.bpg, fname+'.pdf')
        self.gv(fname)

    def test_3_plotNetworks(self):
        self.test_1_init()
        fname = self.fprefix + 'plotNetworks'
        plotNetworks(self.bpg, fname+'.pdf', 0)
        self.gv(fname)

    def test_4_unroll(self):
        self.test_1_init()
        f = open(self.fprefix+'unroll_before.pickle','w')
        pickle.dump(self.bpg, f)
        f.close()
        # root node should be in list
        assert self.bpg.root
        assert self.bpg.bodyparts.index(self.bpg.root) >= 0
        # -> ps
        fname = self.fprefix + 'unroll_before'
        plotBpg(self.bpg, fname+'.dot')
        plotBpg(self.bpg, fname+'.pdf')
        self.gv(fname)
        ur_bpg = self.bpg.unroll()
        ur_bpg.sanityCheck()
        f = open(self.fprefix+'unroll_after.pickle','w')
        pickle.dump(ur_bpg, f)
        f.close()
        # -> ps
        fname = self.fprefix + 'unroll_after'
        plotBpg(ur_bpg, fname+'.dot')
        plotBpg(ur_bpg, fname+'.pdf')
        self.gv(fname)

    def test_5_mutate(self):
        self.test_1_init()
        for _ in range(3):
            self.bpg.mutate(1)

if __name__ == "__main__":
    test_main()
