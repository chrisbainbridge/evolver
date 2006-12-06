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
        self.fprefix = 'test/BodyPartGraph_'

    def tearDown(self):
        pass

    def gv(self, f):
        if test_common.interactive:
            os.system('kghostview %s.ps'%f)

    def test_1_init(self):
        self.bpg = new_individual_fn(**new_individual_args)
        self.bpg.sanityCheck()

    def test_2_plotBpg(self):
        self.test_1_init()
        fname = self.fprefix + '2_plotBpg'
        plotBpg(self.bpg, fname+'.dot')
        os.system('dot -Tps -o %s.ps %s.dot'%(fname, fname))
        self.gv(fname)

    def test_3_unroll(self):
        self.test_1_init()
        f = open(self.fprefix+'3_unroll_before.pickle','w')
        pickle.dump(self.bpg, f)
        f.close()
        # root node should be in list
        assert self.bpg.root
        assert self.bpg.bodyparts.index(self.bpg.root) >= 0
        # -> ps
        fname = self.fprefix + '3_unroll_before'
        plotBpg(self.bpg, fname+'.dot')
        plotBpg(self.bpg, fname+'.ps')
        self.gv(fname)
        ur_bpg = self.bpg.unroll()
        ur_bpg.sanityCheck()
        f = open(self.fprefix+'3_unroll_after.pickle','w')
        pickle.dump(ur_bpg, f)
        f.close()
        # -> ps
        fname = self.fprefix + '3_unroll_after'
        plotBpg(ur_bpg, fname+'.dot')
        plotBpg(ur_bpg, fname+'.ps')
        self.gv(fname)

    def test_4_mutate(self):
        self.test_1_init()
        for _ in range(3):
            self.bpg.mutate(1)

#     def test_BodyPartGraph_createOdeStuff(self):
#         "BodyPartGraph.createOdeStuff"
#         for _ in range(RANDOM_REPEAT):
#             bpg = BodyPartGraph()
#             bpg.createRandom(self.np)
#             bpg.unroll()
#             bpg.createOdeStuff()
#             for bp in bpg.bodyparts:
#                 assert bp._v_ode_body

##     def test_MorphologyEvolver___init__(self):
##         "MorphologyEvolver.__init__"
##         MorphologyEvolver()

##     def test_MorphologyEvolver_createInitialGeneration(self):
##         "MorphologyEvolver.createInitialGeneration"
##         me = MorphologyEvolver()
##         me.createInitialGeneration(3, self.np)
##         assert len(me.generation) == 3

##     def test_MorphologyEvolver_evaluate(self):
##         "MorphologyEvolver.evaluate"
##         me = MorphologyEvolver()
##         me.setSimulator(MovementSim)
##         me.setTrialTime(30)
##         for _ in range(RANDOM_REPEAT):
##             bpg = BodyPartGraph()
##             bpg.createRandom(self.np)
##             ev = Evaluation(bpg)
##             me.evaluate(ev)
##             assert ev.score >= 0

##     def test_MorphologyEvolver_createNextGeneration(self):
##         "MorphologyEvolver.createNextGeneration"
##         for _ in range(RANDOM_REPEAT):
##             me = MorphologyEvolver()
##             me.createInitialGeneration(3, self.np)
##             for e in me.generation:
##                 e.score = random.randint(0,100)
##             me.createNextGeneration()

##     def test_MorphologyEvolver_evolve(self):
##         "MorphologyEvolver.evolve"
##         GENERATIONS = 10
##         for _ in range(RANDOM_REPEAT):
##             me = MorphologyEvolver()
##             me.createInitialGeneration(3, self.np)
##             me.setSimulator(MovementSim)
##             me.setTrialTime(30)
##             me.final_gen_num = GENERATIONS
##             me.evolve()
##             assert me.gen_num == GENERATIONS
##             me.generation.revsort()
##             log.debug('got fitness high %f', me.generation[0].score)

if __name__ == "__main__":
    test_main()
