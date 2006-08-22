#!/usr/bin/python

import unittest
import logging
import random
import sys

import node
import evolve
from test_common import *

evolve.master = 1
rl = logging.getLogger()

class Generation(unittest.TestCase):

    def setUp(self):
        random.seed()

    def tearDown(self):
        pass

    def test_0_create_gen_bpgs(self):
        evolve.Generation(5, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)

    def test_1_evaluate_bpgs(self):
        g = evolve.Generation(5, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)
        g.evaluate(0)
        self.assertTrue(type(g[0].score) is float or type(g[0].score) is int)
        rl.debug('score was %f', g[0].score)

    def test_2_elitistUpdate(self):
        g = evolve.Generation(10, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)
        for x in g:
            #g.evaluate(x)
            x.score = random.uniform(0,10)
        g.update()

##     def test_NetworkEvolver___init__(self):
##         "NetworkEvolver.__init__"
##         NetworkEvolver()

##     def test_NetworkEvolver_createInitialGeneration(self):
##         "NetworkEvolver.createInitialGeneration"
##         for _ in range(RANDOM_REPEAT):
##             ne = NetworkEvolver()
##             ne.createInitialGeneration(3, self.np)
##             assert len(ne.generation) == 3

##     def test_NetworkEvolver_evaluate(self):
##         "NetworkEvolver.evaluate"
##         ne = NetworkEvolver()
##         ne.setSimulator(PoleBalanceSim)
##         ne.setTrialTime(30)
##         for _ in range(RANDOM_REPEAT):
##             n = createNetwork(self.np)
##             ev = Evaluation(n)
##             ne.evaluate(ev)
##             assert ev.score >= 0

##     def test_NetworkEvolver_createNextGeneration(self):
##         "NetworkEvolver.createNextGeneration"
##         for _ in range(RANDOM_REPEAT):
##             ne = NetworkEvolver()
##             ne.createInitialGeneration(3, self.np)
##             for e in ne.generation:
##                 e.score = random.randint(0,100)
##             ne.createNextGeneration()

##     def test_NetworkEvolver_evolve(self):
##         "NetworkEvolver.evolve"
##         for _ in range(RANDOM_REPEAT):
##             ne = NetworkEvolver()
##             ne.createInitialGeneration(3, self.np)
##             ne.setSimulator(PoleBalanceSim)
##             ne.setTrialTime(30)
##             ne.final_gen_num = 3
##             ne.evolve()
##             assert ne.gen_num == 3


suite = unittest.makeSuite(Generation, 'test')

if __name__ == "__main__":
    setup_logging(rl)
    import testoob
    testoob.main()
