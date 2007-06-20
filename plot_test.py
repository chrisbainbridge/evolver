#!/usr/bin/python

import testoob
from unittest import TestCase
from random import random, randint
import sys

from test_common import *
from plot import *

class G:
    def __init__(self):
        self.fitnessList = []
        for i in range(100):
            d = (random(), (i/2)*random(), i*random())
            self.fitnessList.append(d)
        self.mutationStats = []
        for i in range(100):
            d = (random(), randint(0,10), random())
            self.mutationStats.append(d)

data = G()

class PlotTest(TestCase):
    def test_plot_generation_vs_fitness(self):
        plot_generation_vs_fitness(data, 'test/plot_generation_vs_fitness.pdf')
    def test_plot_mutation_vs_prob_improvement(self):
        plot_mutation_vs_prob_improvement(data, 'test/plot_mutation_vs_prob_improvement.pdf')
    def test_plot_mutation_vs_fitness_change(self):
        plot_mutation_vs_fitness_change(data, 'test/plot_mutation_vs_fitness_change.pdf')

if __name__ == "__main__":
    test_main()
