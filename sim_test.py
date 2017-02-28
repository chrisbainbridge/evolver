#!/usr/bin/python

import unittest
import logging
from logging import debug
import random
import os
import sys
import math
import ode
import testoob
import copy

from persistent.list import PersistentList
try:
    from cgkit.cgtypes import vec3
except ImportError:
    from cgtypes import vec3
from Cheetah.Template import Template

import sim
from bpg import Edge, BodyPart, BodyPartGraph
from node import SigmoidNode, LogicalNode
import test_common
from test_common import *
from network import Network
from plot import plotSignals
from qtapp import MyApp

# for motorised joint tests we only have 2 cylinders
import bpg
bpg.MIN_UNROLLED_BODYPARTS=2

myapp = MyApp([sys.argv[0]] + ['-geometry','640x480'])

TESTDIR = '/tmp/'
SECONDS = 3
random.seed(1)
if not os.path.exists('test'):
    os.mkdir('test')

class TestBodyPart(BodyPart):
    """Create a random test BodyPart aligned along z axis"""
    def __init__(self, network_args, jtype='hinge'):
        debug('TestBp.__init__')
        BodyPart.__init__(self, network_args)
        # override some values
        self.scale = 2.0
        self.recursive_limit = 2
        self.joint = jtype

class TestBodyPartGraph(BodyPartGraph):
    "Create a BPG containing num_bodyparts BodyParts"
    def __init__(self, network_args, num_bodyparts, jtype='hinge'):
        debug('TestBpg.__init__')
        self.bodyparts = PersistentList()
        self.unrolled = 0
        debug('Creating %d random BodyParts'%(num_bodyparts))
        p = TestBodyPart(network_args, jtype)
        self.bodyparts.append(p)
        p.isRoot = 1
        self.root = p
        for _ in range(1, num_bodyparts):
            bp = TestBodyPart(network_args, jtype)
            bp.isRoot = 0
            self.bodyparts.append(bp)
            e = Edge(bp, 1, 0)
            p.edges.append(e)
            p = bp
        self.connectInputNodes()

class BpgTestCase(unittest.TestCase):

    def test_0_init(self):
        sim.BpgSim()

    def test_1_addBP(self):
        bp = BodyPart(new_network_args)
        s = sim.BpgSim()
        s.addBP(bp)

    def test_2_add(self):
        b = BodyPartGraph(new_network_args)
        b = b.unroll()
        b.connectInputNodes()
        s = sim.BpgSim()
        s.add(b)

    def test_3_run(self):
        b = BodyPartGraph(new_network_args)
        b = b.unroll()
        b.connectInputNodes()
        s = sim.BpgSim(SECONDS)
        s.add(b)
        s.run()
        assert s.score == -1 or s.score >= 0

    def test_4_run(self):
        b = TestBodyPartGraph(new_network_args, 5, 'hinge')
        s = sim.BpgSim(SECONDS)
        s.add(b)
        s.run()
        assert s.score == -1 or s.score >= 0

    def test_5_siglog(self):
        b = TestBodyPartGraph(new_network_args, 5, 'universal')
        s = sim.BpgSim(SECONDS)
        s.add(b)
        s.relaxed = 1
        siglog = 'test/sim_siglog.trace'
        s.initSignalLog(siglog)
        oldsize = os.path.getsize(siglog)
        s.run()
        newsize = os.path.getsize(siglog)
        assert newsize > oldsize
        plotSignals('test/sim_siglog.trace')

    def test_6_siglog_quanta(self):
        args = copy.deepcopy(new_network_args)
        args['new_node_args']['quanta'] = 4
        b = TestBodyPartGraph(args, 5, 'universal')
        s = sim.BpgSim(SECONDS)
        s.add(b)
        s.relaxed = 1
        siglog = 'test/sim_siglog_quanta.trace'
        s.initSignalLog(siglog)
        oldsize = os.path.getsize(siglog)
        s.run()
        newsize = os.path.getsize(siglog)
        assert newsize > oldsize
        plotSignals('test/sim_siglog_quanta.trace')

    def test_7_run_ca(self):
        args = copy.deepcopy(new_network_args)
        args['new_node_class'] = node.LogicalNode
        args['new_node_args'] = new_node_args_logical
        b = TestBodyPartGraph(args, 5, 'hinge')
        s = sim.BpgSim(SECONDS)
        s.add(b)
        s.run()
        assert s.score == -1 or s.score >= 0

def runVisualSim(sim, record=0, avifile=None):
    "Open the QT renderer and run the simulation"
    myapp.setRecord(record, avifile)
    myapp.setSim(sim)
    myapp.endtime = sim.max_simsecs
    myapp.glwidget.pause = 1
    err = myapp.exec_loop()
    assert not err

def runNonVisualSim(sim):
    sim.run()

def runSim(sim, record=0, avifile=None):
    if test_common.interactive:
        runVisualSim(sim, record, avifile)
    else:
        runNonVisualSim(sim)
    sim.destroy()

def nudgeGeomsInSpace(s):
    "Apply a small force to every geom in space s"
    for i in range(s.space.getNumGeoms()):
        g = s.space.getGeom(i)
        if type(g) is ode.GeomCCylinder:
            f = lambda : random.uniform(0.0, 0.01)
            g.getBody().addForce((f(),f(),f()))

def createAndRunSim(jtype):
    b = TestBodyPartGraph(new_network_args, 5, jtype)
    s = sim.BpgSim(SECONDS)
    s.add(b)
    nudgeGeomsInSpace(s)
    runSim(s)

class BpgSimTestCase(unittest.TestCase):

    def test_1_single_bodypart(self):
        b = TestBodyPartGraph(new_network_args, 1)
        s = sim.BpgSim(SECONDS)
        s.add(b)
        for i in range(s.space.getNumGeoms()):
            g = s.space.getGeom(i)
            if type(g) is ode.GeomCCylinder:
                g.getBody().addForce((0.1,0,0))
        runSim(s)

    def test_2_bodyparts_with_hinge_joints(self):
        createAndRunSim('hinge')

    def test_3_bodyparts_with_universal_joints(self):
        createAndRunSim('universal')

    def test_4_bodyparts_with_ball_joints(self):
        createAndRunSim('ball')

    def do_joint_motor(self, jointtype, record=0):
        b = TestBodyPartGraph(new_network_args, 2, jointtype)
        b.bodyparts[0].rotation = (0, (1,0,0))
        b.bodyparts[1].rotation = (math.pi/2, (0,1,0))
        for i in 0,1:
            b.bodyparts[i].motor_input = None
        s = sim.BpgSim(SECONDS)
        s.relaxed = 1
        s.add(b)
        s.bpgs[0].bodyparts[0].motor_input = None
        s.bpgs[0].bodyparts[1].motor_input = None
        s.world.setGravity((0,0,0))
        s.space.getGeom(0).getBody()
        b1 = s.space.getGeom(1).getBody()
        s.moveBps(0,0,5)
        # fix bp so it cant move
        j = ode.FixedJoint(s.world)
        j.attach(b1, ode.environment)
        j.setFixed()
        # start motor
        m = s.bpgs[0].bodyparts[1].motor
        motor_data = m.log('test/'+jointtype)
        m.dangle[0] = math.pi/2
        m.dangle[1] = math.pi/4
        m.dangle[2] = -math.pi/2
        s.initSignalLog('test/signal.log')
        if not record:
            runSim(s)
        else:
            runSim(s, 1, '%s/record_test.avi'%TESTDIR)
        m.endlog()

        t = Template(file='plot_motor.t')
        t.data = motor_data
        t.out = motor_data[:-4] + '.pdf'
        t.joint = jointtype
        f = open('tmp.r', 'w')
        f.write(t.respond())
        f.close()
        os.system('R -q --no-save < tmp.r >> r.out 2>&1')

    def test_5_hinge_motor(self):
        self.do_joint_motor('hinge')

    def test_6_universal_motor(self):
        self.do_joint_motor('universal')

    def test_7_ball_motor(self):
        self.do_joint_motor('ball')

    def test_8_record_movie(self):
        self.do_joint_motor(jointtype='ball', record=1)
        if test_common.interactive:
            cmd = 'mplayer %s/record_test.avi'%TESTDIR
            if logging.getLogger().level != logging.DEBUG:
                cmd += ' &> /dev/null'
            os.system(cmd)
            os.system('rm %s/record_test.avi'%TESTDIR)

class PoleBalanceSimTestCase(unittest.TestCase):

    def test_1_random_network_control(self):
        s = sim.PoleBalanceSim(SECONDS)
        n = Network(10, 1, 1, SigmoidNode, {}, 'full', 'async', 1, 1)
        n.weights = [random.randrange(-7,7) for i in range(4)]
        s.setNetwork(n)
        runSim(s)

    def test_2_random_network_control_impulse_response(self):
        s = sim.PoleBalanceSim(SECONDS)
        # apply unit impulse
        s.pole_geom.getBody().addForce((1,0,0))
        n = Network(10, 1, 1, SigmoidNode, {}, 'full', 'async', 1, 1)
        n.weights = [random.randrange(-7,7) for i in range(4)]
        s.setNetwork(n)
        runSim(s)

    def test_3_lqr_control_impulse_response(self):
        s = sim.PoleBalanceSim(SECONDS)
        s.setUseLqr()
        runSim(s)

if __name__ == "__main__":
    test_main()
