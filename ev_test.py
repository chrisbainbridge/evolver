#!/usr/bin/python

from unittest import TestCase
import os
import sys
import testoob

import ev
from test_common import *
from logging import debug
import pdb

STDARGS = '-p 3 -t 3 -g 3 --topology 1d --update async --nodes 5'
TESTS = ['-r ev_logical --nodetype logical --states 2',
        '-r ev_sigmoid --nodetype sigmoid',
        '-r ev_sigmoid_q --nodetype sigmoid -q 32',
        '-r ev_steadystate --nodetype sigmoid --steadystate',
        '-r ev_pb --sim pb']

def main(s):
    sys.argv = s.split()
    ev.main()

def delete():
    main('ev.py -r %s -e'%g)

def create():
    main('ev.py -r %s %s'%(g, args))

def run():
    main('ev.py -r %s -c -m'%g)

def plot():
    debug('testing --plotfitness')
    main('ev.py -r %s --plotfitness test/%s-fitness.pdf'%(g, g))
    debug('testing --plotpi')
    main('ev.py -r %s --plotpi test/%s-childpi.pdf'%(g, g))
    debug('testing --plotfc')
    main('ev.py -r %s --plotfc test/%s-childfc.pdf'%(g, g))

class EvTest(TestCase):
    def test_1_delete(self):
        delete()
    def test_2_create(self):
        create()
    def test_3_run(self):
        run()
    def test_4_plot(self):
        plot()

if __name__ == "__main__":
    if '--args' not in sys.argv:
        for args in TESTS:
            cmd = 'ev_test.py --args "%s %s" %s'%(args, STDARGS, ' '.join(sys.argv[1:]))
            print cmd
            os.system(cmd)
    else:
        i = sys.argv.index('--args')
        args = sys.argv[i+1]
        del sys.argv[i:i+2]
        x = args.split()
        g = x[x.index('-r')+1]
        test_main()
