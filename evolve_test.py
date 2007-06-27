#!/usr/bin/python

import unittest
from logging import debug
import random
import sys

import node
import evolve
from test_common import *

random.seed()

class GenerationTest(unittest.TestCase):

    def test_0_create_gen_bpgs(self):
        evolve.Generation(5, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)

    def test_1_evaluate_bpgs(self):
        g = evolve.Generation(5, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)
        g.evaluate(0)
        score = g[0].score
        self.assertTrue(isinstance(score, float) or isinstance(score, int))
        debug('score was %f', score)

    def test_2_elitistUpdate(self):
        g = evolve.Generation(10, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args)
        for x in g:
            #g.evaluate(x)
            x.score = random.uniform(0,10)
        g.update()

    def test_3_steadyState(self):
        g = evolve.Generation(3, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args, 'steady-state')
        g.final_gen_num = 5
        g.runClientLoop(1, 1)

    def test_4_quantised(self):
        new_node_args_sigmoid['quanta'] = 8
        self.test_2_elitistUpdate()

    def test_5_mutation_rate(self):
        g = evolve.Generation(3, new_individual_fn, new_individual_args, new_sim_fn, new_sim_args, 'elite', 0.1)
        g.final_gen_num = 3
        g.runClientLoop()

if __name__ == "__main__":
    test_main()
