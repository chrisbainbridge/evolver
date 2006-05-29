#!/usr/bin/python

import unittest
import logging
import random
import os
import sys
import math
import ode
import testoob

from persistent.list import PersistentList
from cgkit.cgtypes import vec3

import sim
import bpg
import node
from test_common import *
import network

rl = logging.getLogger()

class TestBp(bpg.BodyPart):
    """Create a random test BodyPart aligned along z axis"""
    def __init__(self, network_args, jtype='hinge'):
        rl.debug('TestBp.__init__')
        bpg.BodyPart.__init__(self, network_args)
        # override some values
        self.scale = 2.0
        self.recursive_limit = 2
        self.joint = jtype

class TestBpg(bpg.BodyPartGraph):
    "Create a BPG containing num_bodyparts BodyParts"
    def __init__(self, network_args, num_bodyparts, jtype='hinge'):
        rl.debug('TestBpg.__init__')
        self.bodyparts = PersistentList()
        self.unrolled = 0
        rl.debug('Creating %d random BodyParts'%(num_bodyparts))
        p = TestBp(network_args, jtype)
        self.bodyparts.append(p)
        self.root = p
        for _ in range(1, num_bodyparts):
            bp = TestBp(network_args, jtype)
            self.bodyparts.append(bp)
            e = bpg.Edge(bp, 1, 0)
            p.edges.append(e)
            p = bp
        self.connectInputNodes()

class BpgTestCase(unittest.TestCase):

    def setUp(self):
        s = random.randint(0,1000)
        random.seed(s)

    def test_0_init(self):
        sim.BpgSim()

    def test_1_addBP(self):
        bp = bpg.BodyPart(new_network_args)
        s = sim.BpgSim()
        s.addBP(bp)

    def test_2_add(self):
        b = bpg.BodyPartGraph(new_network_args)
        b = b.unroll()
        b.connectInputNodes()
        s = sim.BpgSim(30)
        s.add(b)

    def test_3_run(self):
        b = bpg.BodyPartGraph(new_network_args)
        b = b.unroll()
        b.connectInputNodes()
        s = sim.BpgSim(30)
        s.add(b)
        s.run()
        assert s.score == -1 or s.score >= 0
        assert s.score == -1 or round(s.total_time) == round(30+s.relax_time)

    def test_4_run(self):
        b = TestBpg(new_network_args, 5, 'hinge')
        s = sim.BpgSim(30)
        s.add(b)
        s.run()
        assert s.score == -1 or s.score >= 0
        assert s.score == -1 or round(s.total_time) == round(30+s.relax_time)

def runVisualSim(sim, record=0, avifile=None, qtargs=[]):
    "Open the QT renderer and run the simulation"
    from qtapp import MyApp
    myapp = MyApp([sys.argv[0]]+qtargs, sim)
    if record and avifile:
        myapp.setRecord(record, avifile)
    myapp.endtime = sim.max_simsecs
    err = myapp.exec_loop()
    assert not err
    myapp.destroy()

def nudgeGeomsInSpace(s):
    "Apply a small force to every geom in space s"
    for i in range(s.space.getNumGeoms()):
        g = s.space.getGeom(i)
        if type(g) is ode.GeomCCylinder:
            f = lambda : random.uniform(0.0, 0.01)
            g.getBody().addForce((f(),f(),f()))

def createAndRunVisualSim(jtype):
    b = TestBpg(new_network_args, 5, jtype)
    s = sim.BpgSim(20)
    s.add(b)
    nudgeGeomsInSpace(s)
    runVisualSim(s)

class VisualTestCase(unittest.TestCase):

    def setUp(self):
        # This ensures that the tests are reproducible identically no matter
        # what order they're run in from the command line
        random.seed()
        
    def tearDown(self):
        # try our best to get rid of the qtapp that won't die...
        import gc
        gc.collect()
        
    def test_1_single_bodypart(self):
        b = TestBpg(new_network_args, 1)
        s = sim.BpgSim(2)
        s.add(b)
        for i in range(s.space.getNumGeoms()):
            g = s.space.getGeom(i)
            if type(g) is ode.GeomCCylinder:
                g.getBody().addForce((0.1,0,0))
        runVisualSim(s)

    def test_2_bodyparts_with_hinge_joints(self):
        createAndRunVisualSim('hinge')

    def test_3_bodyparts_with_universal_joints(self):
        createAndRunVisualSim('universal')

    def test_4_bodyparts_with_ball_joints(self):
        createAndRunVisualSim('ball')

    def do_joint_motor(self, jointtype, record=0):
        b = TestBpg(new_network_args, 2, jointtype)
        b.bodyparts[0].rotation = (0, (1,0,0))
        b.bodyparts[1].rotation = (math.pi/2, (0,1,0))
        for i in 0,1:
            for attr in 'lostop', 'lostop2', 'lostop3', 'histop', 'histop2', 'histop3', 'motor_input':
                setattr(b.bodyparts[i], attr, None)
        s = sim.BpgSim(0)
        s.relax_time = 0
        s.add(b)
        s.bpgs[0].bodyparts[0].motor_input = None
        s.bpgs[0].bodyparts[1].motor_input = None
        s.world.setGravity((0,0,0))
        b0 = s.space.getGeom(0).getBody()
        b1 = s.space.getGeom(1).getBody()
        s.moveBps(0,0,5)
        # fix bp so it cant move
        j = ode.FixedJoint(s.world)
        j.attach(b1, ode.environment)
        j.setFixed()
        # start motor
        m = s.bpgs[0].bodyparts[1].motor
        m.desired_axisangle[0] = math.pi*3/2
        m.desired_axisangle[2] = 5*math.pi/4
        # REMOVEME!!!!
        #b0.addForce((0,0,10000))

        if not record:
            runVisualSim(s)
        else:
            runVisualSim(s, 1, 'test/record_test.avi', ['-geometry','640x480'])

    def test_5_hinge_motor(self):
        self.do_joint_motor('hinge')

    def test_6_universal_motor(self):
        self.do_joint_motor('universal')

    def test_7_ball_motor(self):
        self.do_joint_motor('ball')
    
    def test_8_record_movie(self):
        self.do_joint_motor(jointtype='ball', record=1) 
        cmd = 'mplayer test/record_test.avi'
        if rl.level != logging.DEBUG:
            cmd += ' &> /dev/null'
        os.system(cmd)
        os.system('rm test/record_test.avi')

class PoleBalanceTestCase(unittest.TestCase):

    def setUp(self):
        random.seed()

    def test_1_random_network_control(self):
        s = sim.PoleBalanceSim(0)
        s.network = network.Network(10, 2, 1, node.Sigmoid, {}, 'full', 'async')
        runVisualSim(s)
        
    def test_2_random_network_control_impulse_response(self):
        s = sim.PoleBalanceSim(1)
        # apply unit impulse
        s.pole_geom.getBody().addForce((1,0,0))
        #s.network = network.Network(10, 2, 1, node.Sigmoid, {}, 'full', 'async')
        runVisualSim(s)
        
    def test_3_lqr_control_impulse_response(self):
        s = sim.PoleBalanceSim(0)
        s.setUseLqr()
        runVisualSim(s)

if __name__ == "__main__":
    setup_logging(rl)
    testoob.main()
