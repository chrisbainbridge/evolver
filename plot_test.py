#!/usr/bin/python

import testoob
from unittest import TestCase
import logging
from random import random, randint
import sys

from test_common import *
from plot import *

rl = logging.getLogger()

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
        
g = G()

class PlotTest(TestCase):
    def test_plotGenerationVsFitness(self):
        plotGenerationVsFitness(g, 'test/test_plotGenerationVsFitness.pdf')
    def test_plotMutationVsProbImprovement(self):
        plotMutationVsProbImprovement(g, 'test/test_plotMutationVsProbImprovement.pdf')
    def test_plotMutationVsFitnessChange(self):
        plotMutationVsFitnessChange(g, 'test/test_plotMutationVsFitnessChange.pdf')

if __name__ == "__main__":
    setup_logging(rl)
    testoob.main()
