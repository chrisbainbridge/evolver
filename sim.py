"""Different simulations that can be attached to neural networks and run."""

import math
import random
import logging

import ode
from pyode_fix import *
from cgkit.cgtypes import quat, mat3, mat4, vec3
from numpy import matrix
#from trace import trace
import bpg
import node
import network
import pdb

CYLINDER_RADIUS = 1.0
CYLINDER_DENSITY = 3.0
MAX_UNROLLED_BODYPARTS = 20
SOFT_WORLD = 1
JOINT_MAXFORCE = 6 * CYLINDER_DENSITY * CYLINDER_RADIUS # product with density and cylinder lengths

log = logging.getLogger('sim')
log.setLevel(logging.INFO)

class MyMotor(ode.AMotor):
    def __init__(self, world):
        ode.AMotor.__init__(self, world)
        self.desired_axisangle = [0.0, 0.0, 0.0]
        self.setParam(ode.ParamFMax, 0.0)
        self.setParam(ode.ParamFMax2, 0.0)
        self.setParam(ode.ParamFMax3, 0.0)
        self.old_angles = [0.0, 0.0, 0.0]

    def step(self):
        log.debug('MyMotor.step')

        x = self.getAngle(0) % (2*math.pi)
        y = self.getAngle(1) % (2*math.pi)
        z = self.getAngle(2) % (2*math.pi)
        dx = self.desired_axisangle[0] % (2*math.pi)
        dy = self.desired_axisangle[1] % (2*math.pi)
        dz = self.desired_axisangle[2] % (2*math.pi)
        log.debug('MyMotor angles=(%f,%f,%f) desired_angles=(%f,%f,%f)'%(x, y, z, dx, dy, dz))
        
        vs =[0,0,0]
        for (x, param) in (0, ode.ParamVel), (1, ode.ParamVel2), (2, ode.ParamVel3):
            a = self.getAngle(x) % (2*math.pi)
            b = self.desired_axisangle[x] % (2*math.pi)
            # go shortest way - figure out direction
            dist = abs(a-b)
            d = -1
            if dist < math.pi and a <= b or dist >= math.pi and a > b:
                    d = 1

          # ignore axes that we don't control for each joint
            if type(self.joint) is ode.HingeJoint and x != 2 \
            or type(self.joint) is ode.UniversalJoint and x == 2:
                self.setParam(param, 0) 
            else:
                # Proportional derivative controller. We have to estimate the 
                # angular velocity because Motor.getAngleRate() is unimplemented
                # and joint.getAngleRate only works for HingeJoint
                ang_vel = abs(a - self.old_angles[x])*50 # FIXME: hardcoded sim frequency 50hz
                self.old_angles[x] = a
                Kp = 10.0 # proportional constant
                Kd = 7.0 # derivative constant
                v = Kp * dist - Kd * ang_vel
#                b0 = self.getBody(0)
#                b1 = self.getBody(1)
#                log.debug('torque0=%f', vec3(b0.getTorque()).length())
#                log.debug('torque1=%f', vec3(b1.getTorque()).length())
#                lv0 = vec3(b0.getLinearVel()).length()
#                lv1 = vec3(b1.getLinearVel()).length()
#                print 'lv0=',lv0
#                print 'lv1=',lv1
#                max_lv = max(lv0, lv1)
#                v -= 0.5 * max_lv
                v = max(v, 0)
                vs[x]= d*v
#                print v
                #print 'x=%f,a=%f,b=%f,dist=%f'%(x,a,b,dist)
                self.setParam(param, d*v)
#                print d*v
#                self.addTorques()
#            print 'vs=',vs
#            self.addTorques(vs[0], vs[1], vs[2])

class Sim(object):
    "Simulation class, responsible for everything in the physical sim."

    def __init__(self, max_simsecs):
        log.debug('Sim.__init__(max_simsecs=%s)', max_simsecs)
        # create world, set default gravity, geoms, flat ground, spaces etc.
        assert type(max_simsecs) is float or type(max_simsecs) is int
        self.total_time = 0.0
        self.max_simsecs = float(max_simsecs)
        self.dt = 1.0/50 # 1/50th second
        self.world = ode.World()
        if SOFT_WORLD:
#            self.world.setCFM(10**-3) # was 10**-3
#            self.world.setERP(0.1) # was 0.1
            self.world.setCFM(10**-6) # was 10**-3
            self.world.setERP(0.2) # was 0.1
        self.world.setGravity((0, 0, -9.8))
        #self.world.setGravity((0,0,-3))
        # space is a holder geom for other geoms
        self.space = ode.SimpleSpace()
        # contactgroup holds contacts when bodies collide
        self.contactgroup = ode.JointGroup()
        # create unmovable floor
        self.ground = ode.GeomPlane(self.space, (0, 0, 1), 0)
        # create the default jointgroup
        # defaults
        self.score = 0.0
        self.finished = 0
        self.siglog = None
        self.bpgs = []

    def run(self):
        log.debug('Sim.run (secs=%f, dt=%f)', self.max_simsecs, self.dt)
        log.debug('num geoms = %d', self.space.getNumGeoms())
        while not self.finished:
            self.step()

class BpgSim(Sim):
    "Simulate articulated bodies built from BodyPartGraphs"

    def __init__(self, max_simsecs=30.0):
        self.relax_time = 0
        Sim.__init__(self, max_simsecs)
        log.debug('BPGSim.__init__')
        self.geom_contact = {}
        self.startpos = vec3(0, 0, 0) 
        self.relaxed = 0
        self.prev_v = []

    # max_simsecs attribute. add relax time to the sim time when set. 
    # return the real full sim time so that it can be rendered correctly.
    def max_simsecs():
        def fget(self):
            return self.max_simsecs_value
        def fset(self, v):
            if v == 0:
                self.max_simsecs_value = 0
            else:
                self.max_simsecs_value = self.relax_time + v
        return locals()
    max_simsecs = property(**dict(max_simsecs()))

    def doSignalLog(self, fname):
        self.siglog = open(fname, 'w')
        assert self.bpgs
        s = '# time '
        # FIXME: will need to change this when we have more than 1 bpg
        for bg in self.bpgs:
            for bp in bg.bodyparts:
                for n in bp.network:
                    s += 'bp%d-%d'%(bg.bodyparts.index(bp), bp.network.index(n))
                    if n in bp.network.inputs:
                        s += 'i'
                    if n in bp.network.outputs:
                        s += 'o'
                    s += ' '
        s += '\n'
        self.siglog.write(s)

            
        # add signals and then write header
        # what are the signals?
        # all neuron values. inputs and outputs should be labelled with what
        # they are connected to.
        #siglog.

    def addBP(self, bp, parent=None, joint_end=None):
	"""Recursively add BodyParts to the simulation.

        bp -- current BodyPart to process
        parent -- parent BP to add to
        joint_end -- which end of the parent ccylinder we should add to"""

        log.debug('addBP')
        body = ode.Body(self.world)
        mass = ode.Mass()
        if not parent:
            # if this is the root we have an absolute length,
            # root scale is relative to midpoint of min..max
            bp.length = bp.scale*(bpg.BP_MIN_LENGTH+(bpg.BP_MAX_LENGTH-bpg.BP_MIN_LENGTH)/2)
        else:
            # otherwise child scale is relative to parent
            bp.length = parent.length * bp.scale
        # limit the bp length
        bp.length = min(bp.length, bpg.BP_MAX_LENGTH)
        # mass along x axis, with length without caps==bp.length
        # arg 3 means aligned along z-axis - must be same in renderer and Geoms
        mass.setCappedCylinder(CYLINDER_DENSITY, 3, CYLINDER_RADIUS, bp.length)
        # attach mass to body
        body.setMass(mass)
        # create Geom
        # aligned along z-axis by default!!
        geom = ode.GeomCCylinder(self.space, CYLINDER_RADIUS, bp.length)
        self.geom_contact[geom] = 0 
        # remember parent for collison detection
        if not parent:
            geom.parent = None
        else:
            geom.parent = parent.geom
        # attach geom to body
        geom.setBody(body)
        log.debug('created CappedCylinder(radius=%f, len=%f)', CYLINDER_RADIUS, bp.length)
        # assert(not in a loop)
        assert not hasattr(bp, 'geom')
        # ref geom from bodypart (used above to find parent geom)
        bp.geom = geom

        # set rotation
        (radians, v) = bp.rotation
        log.debug('radians,v = %f,%s', radians, str(v))
        q = quat(radians, vec3(v))
        rotmat = q.toMat3()
        if parent:
            # rotate relative to parent
            p_r = mat3(parent.geom.getRotation()) # joint_end *
            log.debug('parent rotation = %s', str(p_r))
            rotmat = p_r * rotmat
        geom.setRotation(rotmat.toList(rowmajor=1))
        log.debug('r=%s', str(rotmat))
        geom_axis = rotmat * vec3(0, 0, 1)
        log.debug('set geom axis to %s', str(geom_axis))
        (x, y, z) = geom.getBody().getRelPointPos((0, 0, bp.length/2.0))
        log.debug('real position of joint is %f,%f,%f', x, y, z)
        # set position
        if not parent:
            # root  - initially located at 0,0,0
            # (once the model is constructed we translate it until all
            # bodies have z>0)
            geom.setPosition((0, 0, 0))
#            geom.parent_joint = None
            #geom.motor = None
            log.debug('set root geom x,y,z = 0,0,0')
        else:
            # child - located relative to the parent. from the
            # parents position move along their axis of orientation to
            # the joint position, then pick a random angle within the
            # joint limits, move along that vector by half the length
            # of the child cylinder, and we have the position of the
            # child.
            # vector from parent xyz is half of parent length along
            # +/- x axis rotated by r
            p_v = vec3(parent.geom.getPosition())
            p_r = mat3(parent.geom.getRotation())
            p_hl = parent.geom.getParams()[1]/2.0 # half len of par
            j_v = p_v + p_r * vec3(0, 0, p_hl*joint_end) # joint vector
            # rotation is relative to parent
            # XXX
            c_v = j_v + rotmat * vec3(0, 0, bp.length/2.0) # joint_end*
            geom.setPosition(tuple(c_v))
            log.debug('set geom x,y,z = %f,%f,%f', c_v[0], c_v[1], c_v[2])

            jointclass = { 'hinge':ode.HingeJoint, 
                           'universal':ode.UniversalJoint, 
                           'ball':ode.BallJoint }
            j = jointclass[bp.joint](self.world)
            # attach bodies to joint
            j.attach(parent.geom.getBody(), body)
            # set joint position
            j.setAnchor(j_v)
            geom.parent_joint = j

            # create motor and attach to this geom
            motor = MyMotor(self.world)
            motor.joint = j
            bp.motor = motor
            motor.attach(parent.geom.getBody(), body)
            #motor.attach(body, parent.geom.getBody())
            # geom.motor = motor
            #self.motor = motor
            motor.setMode(ode.AMotorEuler)

            # set joint stops
            stop_attrs = { 'lostop' : ode.ParamLoStop, 
                            'histop' : ode.ParamHiStop, 
                            'lostop2' : ode.ParamLoStop2, 
                            'histop2' : ode.ParamHiStop2, 
                            'lostop3' : ode.ParamLoStop3, 
                            'histop3' : ode.ParamHiStop3 }
            for ls, hs in (('lostop', 'histop'), ('lostop2', 'histop2'), ('lostop3', 'histop3')):
                l = getattr(bp, ls)
                h = getattr(bp, hs)
                if type(l) in [float, int]:
                    motor.setParam(stop_attrs[ls], l)
                if type(h) in [float, int]:
                    motor.setParam(stop_attrs[hs], h)

            # set joint axes
            maxforce = JOINT_MAXFORCE * bp.length * parent.length
            log.debug('maxforce = %f', maxforce)
            # hmmm, seems ridiculously large
            #print 'maxforce=',maxforce
            if bp.joint == 'hinge':
                # we have 3 points - parent body, joint, child body
                # find the normal to these points
                # (hinge only has 1 valid axis!)
                axis1 = ((j_v-p_v).cross(j_v-c_v)).normalize()
                log.debug('setting hinge joint axis to %s', axis1)
                log.debug('hinge axis = %s', j.getAxis())
                axis_inv = rotmat.inverse()*axis1
                axis2 = vec3((0, 0, 1)).cross(axis_inv)
                log.debug('hinge axis2 = %s', axis2)
                j.setAxis(tuple(axis1))
                # some anomaly here.. if we change the order of axis2 and axis1,
                # it should make no difference. instead there appears to be an
                # instability when the angle switches from -pi to +pi
                # so.. use parameter3 to control the hinge
                # (maybe this is only a problem in the test case?)
                motor.setAxis(0, 1, tuple(axis2))
                motor.setAxis(2, 2, tuple(rotmat*axis1))
                motor.setParam(ode.ParamFMax, 0)
                motor.setParam(ode.ParamFMax2, 0)
                motor.setParam(ode.ParamFMax3, maxforce)
                
            elif bp.joint == 'universal':
                # bp.axis1/2 is relative to bp rotation, so rotate axes
                axis1 = rotmat * vec3(bp.axis1)
                axis2 = rotmat * vec3(bp.axis2)
                j.setAxis1(tuple(axis1))
                j.setAxis2(tuple(axis2))
                # rotate about the first and third parameters for these axis
                motor.setAxis(0, 1, tuple(axis1))
                motor.setAxis(2, 2, tuple(axis2))
                motor.setParam(ode.ParamFMax, maxforce)
                motor.setParam(ode.ParamFMax2, maxforce)
                motor.setParam(ode.ParamFMax3, 0)
            elif bp.joint == 'ball':
                # the ball rotation is an evolvable parameter, so the joint axes
                # do evolve 
                ball_rot = quat(bp.ball_rot[0], vec3(bp.ball_rot[1])).toMat3()
                x = ball_rot * vec3((1, 0, 0))
                y = ball_rot * vec3((0, 1, 0))
                motor.setAxis(0, 1, tuple(x))
                motor.setAxis(2, 2, tuple(y))
                motor.setParam(ode.ParamFMax, maxforce)
                motor.setParam(ode.ParamFMax2, maxforce)
                motor.setParam(ode.ParamFMax3, maxforce)

            log.debug('created joint with parent at %f,%f,%f', j_v[0], j_v[1], j_v[2])

        # recurse on children
        #geom.joint_end = joint_end
        geom.child_joint_ends = set([ e.joint_end for e in bp.edges ])
#        if joint_end != None:
#            geom.joint_ends.add(joint_end)
        geom.parent_joint_end = joint_end

        geom.friction_left = bp.friction_left
        geom.friction_right = bp.friction_right
        if joint_end == None:
            # root
            if -1 in geom.child_joint_ends:
                geom.left = 'internal'
            else:
                geom.left = 'external'
            if 1 in geom.child_joint_ends:
                geom.right = 'internal'
            else:
                geom.right = 'external'
        else:
            # not root
            geom.left = 'internal'
            if 1 in geom.child_joint_ends:
                geom.right = 'internal'
            else:
                geom.right = 'external'

        #print 'je=',geom.joint_ends
#        if joint_end == None:
#            #print 'root,bp.edges=',bp.edges
#            geom.root = 1
        for e in bp.edges:
            self.addBP(e.child, bp, e.joint_end)

    def __del__(self):
        log.debug('Sim.__del__()')
        # destroy hanging geoms
        ode._geom_c2py_lut.clear()

    def add(self, bpgraph):
        """Add BodyPartGraph to simulation.
        Sim needs to convert into a simulatable object by:

          * Unroll bodypart graph
          * Create a graph of geoms
          * Each bp has a network"""

        log.debug('add(%s)', bpgraph)
        log.debug('%s', bpgraph.__class__)
        assert isinstance(bpgraph, bpg.BodyPartGraph)
        if not bpgraph.unrolled:
            bpgraph = bpgraph.unroll()
            bpgraph.connectInputNodes()
        bpgraph.sanityCheck()

        num_bps = len(bpgraph.bodyparts)
        log.debug('BPGSim.setSolution: number of unrolled bodyparts = %d', num_bps)
        if num_bps > MAX_UNROLLED_BODYPARTS:
            log.warn('BPGSim.setSolution: num_bps (%d) > MAX_UNROLLED_BODYPARTS (%d)', 
                         num_bps, 
                         MAX_UNROLLED_BODYPARTS)
            log.warn('Pruning bodyparts!')
            while num_bps > MAX_UNROLLED_BODYPARTS:
                # randomly remove bodyparts.. this should mix things up a bit
                # and encourage smaller BPGs
                num_bps = len(bpgraph.bodyparts)
                i = random.randint(0, num_bps-1)
                del bpgraph.bodyparts[i]
            # fixup the unrolled, pruned bpg
            bpgraph.fixup()

        assert bpgraph.root
        # recursively add all bodyparts
        self.addBP(bpgraph.root)
        self.raiseGeoms()
        # initialise the networks into random state
        for bp in bpgraph.bodyparts:
            bp.network.randomiseState()
        self.bpgs.append(bpgraph)

    def raiseGeoms(self):
        "Raise all geoms above the ground"
        total_offset = 0.0
        min_z = None
        # big raise
        for g in self.space:
            if g != self.ground:
                (x, y, z) = g.getPosition()
                if min_z == None:
                    min_z = z
                else:
                    min_z = min(min_z, z)
        if min_z != None:
            self.moveBps(0, 0, -min_z)
            total_offset += -min_z
            log.debug('big model raise by %f', -min_z)
        # small raises until all geoms above ground
        incontact = 1
        while incontact:
            # is model in contact with the ground?
            incontact = 0
            for i in range(self.space.getNumGeoms()):
                g = self.space.getGeom(i)
                if g != self.ground:
                    (x, y, z) = g.getPosition()
                    incontact = ode.collide(self.ground, g)
                    if incontact:
                        break
            if incontact:
                self.moveBps(0, 0, 0.1)
                total_offset += 0.1
        log.debug('raised model to %f', total_offset)

    def moveBps(self, x, y, z):
        for i in range(0, self.space.getNumGeoms()):
            geom = self.space.getGeom(i)
            if geom.placeable():
                (gx, gy, gz) = geom.getPosition()
                geom.setPosition((gx+x, gy+y, gz+z))

    def fitnessMeanZ(self):
        # fitness is mean z over bodies over time
        total_z = 0.0
        count = 0
        for i in range(self.space.getNumGeoms()):
            geom = self.space.getGeom(i)
            if type(geom) is not ode.GeomPlane:
                (x, y, z) = geom.getPosition()
                total_z += z
                count += 1
        self.score += total_z

    def fitnessMeanDistance(self):
        total = 0.0
        count = 0
        for i in range(self.space.getNumGeoms()):
            geom = self.space.getGeom(i)
            if type(geom) is not ode.GeomPlane:
                (x, y, z) = geom.getPosition()
                total += math.sqrt(x**2+y**2+z**2) 
                count += 1
        self.score += total/count

    def meanPos(self, bpg):
        tx = 0.0
        ty = 0.0
        tz = 0.0
        for bp in bpg.bodyparts:
            (x, y, z) = bp.geom.getPosition()
            tx += x
            ty += y
            tz += z
        return vec3(tx, ty, tz) / len(bpg.bodyparts)

    def fitnessDistFromOrigin(self):
        "Geometric distance from post-relax start position"
#        total = 0.0
#        count = 0
#        mindist = None 

#        if self.total_time > self.relax_time:
#        if self.startpos == None:
#            self.startpos = self.meanPos(self.bpgs[0])
#            log.debug('post-relax pos = %s', str(self.startpos))
                    
        mpos = self.meanPos(self.bpgs[0])
        self.score = (mpos - self.startpos).length()
#            print 'X startpos =', self.startpos
#            print 'X curpos =', mpos - self.startpos
#            print 'X score = ', self.score
            
            
#            if mindist == None:
#                mindist = o.length()
#            else:
#                mindist = min(mindist, o.length())
#
#        if mindist == None:
#            self.score = -1
#        else:
#            self.score = mindist

    def updateFitness(self):
        try:
            # FIXME: command line argument
            #self.fitnessMeanZ()
            # self.fitnessMeanDistance()
            self.fitnessDistFromOrigin()
        except OverflowError:
            # self.score = -1.0
            self.finished = 1
        if type(self.score) not in [float, int]:
            log.critical('score is %s', self.score)
            assert type(self.score) in [float, int]

    def collision_callback(self, args, geom1, geom2):
        "Callback function for the geometry collide() method"
        # calculate intersection points
        contacts = ode.collide(geom1, geom2)
        for c in contacts:
            mu = 0 # default
            log.debug('collision: creating contact between %s %s', str(geom1), str(geom2))
            #if SOFT_WORLD:
            #    c.setSoftCFM(10**-8) # -4
                #c.setMode(c.getMode() | ode.ContactSoftCFM)
            #c.setMode(c.getMode() | ode.ContactBounce)
            #c.setBounce(0.1)
            if type(geom1) is ode.GeomCCylinder and type(geom2) is ode.GeomCCylinder:
                # no collision detect between body parts!
                return
#                if geom1.parent is geom2 or geom2.parent is geom1:
#                    log.debug('ignoring contact between jointed geoms')
#                    return

            (cpos, cnor, cdep, cg1, cg2) = c.getContactGeomParams()
            if (type(geom1) is ode.GeomPlane and type(geom2) is ode.GeomCCylinder) or (type(geom1) is ode.GeomCCylinder and type(geom2) is ode.GeomPlane):
                # intersection between cylinder and the ground
                if type(geom1) is ode.GeomCCylinder:
                    cylinder = geom1
                elif type(geom2) is ode.GeomCCylinder:
                    cylinder = geom2
                # find endpoints of cylinder
                r = mat3(cylinder.getRotation())
                p = vec3(cylinder.getPosition())
                (radius, length) = cylinder.getParams()
                # is collision point c in an endpoint?
                ep0 = p + r*vec3(0, 0, -length/2)
                ep1 = p + r*vec3(0, 0, +length/2)
                (cpos, cnor, cdep, cg1, cg2) = c.getContactGeomParams()
                # is cpos in sphere around ep0 or ep1?
                epc = None
                for ep in ep0, ep1:
                    cpos = vec3(cpos)
                    d2 = (cpos-ep).length()
                    if (d2 <= radius**2*1.01):
                        epc = ep
                # friction mu is from evolved bp
                if epc == ep0:
                    mu = cylinder.friction_left
                elif epc == ep1:
                    mu = cylinder.friction_right
            c.setMu(mu)
            j = ode.ContactJoint(self.world, self.contactgroup, c)
            j.attach(geom1.getBody(), geom2.getBody())
            self.geom_contact[geom1] = 1
            self.geom_contact[geom2] = 1

    def relax(self):
        "Relax bpg until total velocity is less than some threshold."
        count = 0
        while 1:
            self.contactgroup.empty()
            self.space.collide(None, self.collision_callback)
            self.world.step(self.dt)
            self.total_time += self.dt
            
            total = 0
            for g in self.space:
                if type(g) is not ode.GeomPlane:
                    b = g.getBody()
                    v = b.getLinearVel()
                    total += vec3(v).length()
#            print abs(total - self.prev_total)
#            if abs(total - self.prev_total) < 0.0001:
            min_rt = 50 * 2
            if len(self.prev_v) < min_rt:
                self.prev_v += [total]
            else:
                self.prev_v = self.prev_v[1:] + [total]
#                print sum(self.prev_v), self.prev_v
                if sum(self.prev_v) < 0.005:
                    self.relaxed = 1
                    self.startpos = self.meanPos(self.bpgs[0])
                    log.debug('relaxed - time=%f, startpos=%s, vt=%f', self.total_time, self.startpos, sum(self.prev_v))
                    break
            count += 1
            if count > 50 * 10:
                # if there are opposing violated constraints the body can move
                # constantly. We don't want that - we want the networks to
                # generate all of the movement energy. So we timeout after 10
                # seconds of waiting for the body to be still, and quit.
                return 1

    def step(self):
        """Sim loop needs to:

          * Go through all BodyParts, update all InputNodes with connected
            Sensor or OutputNode values.

          * Go through all BodyParts, and do a sync or async step
            of every Network.

          * Go through all BodyParts, for each motor, find connected
            OutputNode (if any) and get value."""

        for g in self.space:
            if g.placeable():
                v = vec3(g.getBody().getLinearVel())
                if v.length() > 150:
                    # blew up, early exit
                    self.score = -1
                    self.finished = 1
                    return
                
                
        if not self.relaxed:
            e = self.relax()
            if e:
                self.score = -1
                self.finished = 1
                return
                
        # detect collisions - calculate contact joints
        for g in self.geom_contact:
            self.geom_contact[g] = 0
        self.space.collide(None, self.collision_callback)
        if 1: #self.total_time > self.relax_time:
            # update sensory input values
            for bpgraph in self.bpgs:
                for bp in bpgraph.bodyparts:
                    # update network external_input nodes
                    if bp.joint == 'hinge':
                        motors = ['MOTOR_2']
                    elif bp.joint == 'universal':
                        motors = ['MOTOR_0', 'MOTOR_1' ]
                    elif bp.joint == 'ball':
                        motors = ['MOTOR_0', 'MOTOR_1', 'MOTOR_2']
                    for n in bp.network.inputs + motors:

                        if isinstance(n, node.Node):
                            (sbp, src) = n.external_input
                        elif isinstance(n, str) and n[:5] == 'MOTOR' and hasattr(bp, 'motor') and bp.motor_input:
                            mi = ord(n[6])-ord('0')
                            (sbp, src) = bp.motor_input[mi]
                        # need value to n n.external_input from src
                        # find the value from simulator, domain is 0..1
                        if src == 'CONTACT':
                            # sbp in contact with anything?
                            value = self.geom_contact[sbp.geom]
                        elif type(src) is str and src[:6] == 'JOINT_':
                            # sbp joint angle
                            if not hasattr(sbp.geom, 'motor'):
                                # this is the root; no joint with parent.
                                value = 0
                            elif src == 'JOINT_0':
                                # angle of joint 0 with parent
                                value = sbp.motor.getAngle(0)
                            elif src == 'JOINT_1':
                                # angle of joint 1
                                value = sbp.motor.getAngle(1)
                            elif src == 'JOINT_2':
                                # angle of joint 2
                                value = sbp.motor.getAngle(2)
                            # scale value to [0,1]
                            value = (value/math.pi+1)/2
                        elif isinstance(src, node.Node):
                            # network output node, in domain [0,1]
                            value = src.output
                        assert 0 <= value <= 1
                        # gaussian noise on sensors and motors
                        value = random.gauss(value, 0.01)
                        if value < 0: value = 0
                        if value > 1: value = 1
                        # send the value to the right place
                        if isinstance(n, node.Node):
                            # put value on neuron output
                            n.output = value
                        elif isinstance(n, str) and n[:5] == 'MOTOR' and hasattr(bp, 'motor') and bp.motor_input:
                            # send value to motor
                            v = (value*2-1)*math.pi
                            bp.motor.desired_axisangle[mi] = v
#                            print 'angle =',v

            # step networks. async or sync
            for bg in self.bpgs:
                for bp in bg.bodyparts:
                    bp.network.step()

            # step motors
            for bg in self.bpgs:
                for bp in bg.bodyparts:
                    if hasattr(bp, 'motor'):
                        bp.motor.step()

            # log signal values
            s = '%f '%(self.total_time)
            if self.siglog:
                for bg in self.bpgs:
                    for bp in bg.bodyparts:
                        for n in bp.network:
                            s += '%f '%(n.output)
                s += '\n'
                self.siglog.write(s)
        # step ode
        self.world.step(self.dt)
        # Remove all contact joints
        self.contactgroup.empty()
        self.total_time += self.dt
        log.debug('stepped world by %f time is %f', self.dt, self.total_time)
        # check if simulation blew up 
        nan = [g for g in self.space if g.placeable() for p in g.getPosition() if str(p)=='nan']
        if nan and self.max_simsecs != 0:
            self.finished = 1
        elif self.total_time > self.max_simsecs and self.max_simsecs != 0:
            self.finished = 1
        elif self.total_time > self.relax_time:
            self.updateFitness()
            
    #def enableTrace(self):
        #self.trace = 1
        #trace.declareSignals(['des_v','force'])

#    def createBox(self, name, (sx,sy,sz), density, (px,py,pz)):
#        """Create a box with ODE body and collision geometry.
#
#        The box Geom will be added to the self.geoms dict.
#        Keyword arguments:
#        name -- a unique name for the box.
#        (sx,sy,sz) -- size
#        density
#        (px,py,pz) -- initial position"""
#        body = ode.Body(self.world)
#        mass = ode.Mass()
#        mass.setBox(density, sx, sy, sz)
#        body.setMass(mass)
#        geom = ode.GeomBox(self.space,(sx, sy, sz))
#        geom.setBody(body)
#        body.setPosition((px,py,pz))
#        return geom

class LqrController:
    def __init__(self):
        """Create LQR controller.
        
        The control matrix was derived in Octave.
        The NBAR input amplification factor was found through trial and error."""
        self.NBAR = -202.25
        self.K = matrix([[-202.25, -304.63, 2349.83, 1402.09]])
        self.U = 0.0
        
    def calculateResponse(self, state):
        "Return error force correction from LQR control matrix applied to state"
        fe = self.NBAR * self.U - self.K * state  
        return fe
        
    def setReferenceInput(self, U):
        "Set the reference input - in this case, the desired cart position."
        self.U = U

class PoleBalanceSim(Sim):
    """Simulation of a pole balancing task.

    Controllers attached to this object require:

      Inputs[0] -- angle of hinge joint between the boxes
      Outputs[0] -- desired velocity of the horizontal travelling box"""

    def __init__(self, max_simsecs=30, net=None):
        """Creates the ODE and Geom bodies for this simulation"""
        Sim.__init__(self, max_simsecs)
        log.debug('init PoleBalance sim')
        self.network = net
        
        CART_POSITION = (0, 0, 2)
        POLE_POSITION = (0, 0, 3+(5.0/2))
        CART_SIZE = (8, 8, 2)
        POLE_SIZE = (1, 1, 5)
        HINGE_POSITION = (0, 0, 3)
        CART_MASS = 10
        POLE_MASS = 0.5
        
        self.INIT_U = [10000]
        
        self.cart_geom = ode.GeomBox(self.space, CART_SIZE)
        self.cart_body = ode.Body(self.world)
        self.cart_body.setPosition(CART_POSITION)
        cart_mass = ode.Mass()
        cart_mass.setBoxTotal(CART_MASS, CART_SIZE[0], CART_SIZE[1], CART_SIZE[2])
        self.cart_body.setMass(cart_mass)
        self.cart_geom.setBody(self.cart_body)
        
        self.pole_geom = ode.GeomBox(self.space, POLE_SIZE)
        self.pole_body = ode.Body(self.world)
        self.pole_body.setPosition(POLE_POSITION)
        pole_mass = ode.Mass()
        pole_mass.setBoxTotal(POLE_MASS, POLE_SIZE[0], POLE_SIZE[1], POLE_SIZE[2])
        self.pole_body.setMass(pole_mass)
        self.pole_geom.setBody(self.pole_body)
        
        self.cart_geom.setCategoryBits(long(0))
        self.pole_geom.setCategoryBits(long(0))
        
        # joint 0 - slide along 1D
        self.slider_joint = ode.SliderJoint(self.world)
        self.slider_joint.attach(self.cart_body, ode.environment)
        self.slider_joint.setAxis((1, 0, 0))
#        self.slider_joint.setParam(ode.ParamFMax, 100)
        self.slider_joint.setParam(ode.ParamLoStop, -5)
        self.slider_joint.setParam(ode.ParamHiStop, 5)
        
        # joint 1 - hinge between the two boxes
        self.hinge_joint = ode.HingeJoint(self.world)
        self.hinge_joint.attach(self.cart_body, self.pole_body)
        self.hinge_joint.setAnchor(HINGE_POSITION)
        self.hinge_joint.setAxis((0, 1, 0))
        
        self.last_hit = 0.0
        self.init_u_count = 0
        self.regular_random_force = 0
        self.lqr = None

    def setUseLqr(self):
        self.lqr = LqrController()
        
    def add(self, net):
        self.setNetwork(net)

    def setNetwork(self, net):
        """Tell PoleSim to use this network.

        Must have 1 input and 1 output"""

        assert type(net) is network.Network
        self.network = net
        self.network.randomiseState()
        self.finished = 0
        # fake external_input connection so node knows its an input
        for n in self.network:
            if n in self.network.inputs:
                n.external_input = 'ANGLE_0'
            else:
                n.external_input = None

#    def doSignalLog(self, fname):
#        # log signal values
#        #print 'x', self.network[2].output
#        s = '%f '%(self.total_time)
#        if self.siglog:
#            for n in self.network:
#                s += '%f '%(n.output)
#            s += '\n'
#            self.siglog.write(s)
#            
#        self.siglog = open(fname, 'w')
#        s = '# time '
#        for n in self.network:
#            s += 'n%d'%self.network.index(n)
#            if n in self.network.inputs:
#                s += 'i'
#            if n in self.network.outputs:
#                s += 'o'
#            s += ' '
#        s += '\n'
#        self.siglog.write(s)

    def applyLqrForce(self):
        # construct state vector (x, xdot, theta, thetadot)
        state = matrix([[self.cart_body.getPosition()[0]], 
                        [self.cart_body.getLinearVel()[0]], 
                        [self.hinge_joint.getAngle()], 
                        [self.hinge_joint.getAngleRate()]]) 
        # calculate and apply input force from LQR control matrix
        fx = self.lqr.calculateResponse(state)
        if self.init_u_count < len(self.INIT_U):
            fx += self.INIT_U[self.init_u_count]
            self.init_u_count += 1
        self.cart_body.addForce((fx, 0, 0))

    def applyNetworkForce(self):
        scaled_angle = (self.hinge_joint.getAngle() + math.pi/4)/(math.pi/2)
#        angle = random.gauss(angle, 0.01) # random noise
        scaled_angle = max(0, min(scaled_angle, 1)) # clip
        # send angle to network
        self.network.inputs[0].output = scaled_angle
        self.network.step()
        # read network, get desired force/velocity
        v = self.network.outputs[0].output
        v = min(1, max(0, random.gauss(v, 0.01))) # add gaussian noise
        v = (v-0.5)*50 # map [0,1] -> [-25,25]
        self.slider_joint.setParam(ode.ParamVel, v)
        self.cart_body.addForce((v, 0, 0))

    def applyRandomForce(self):
        # hit the pole with a random force
        force = (random.random() - 0.5) # hit with a very small force
#        *self.total_time**2 # weight by time, so gets more difficult
        force *= 20
        #print force
        self.pole_body.addForce((force, 0, 0))
        self.last_hit = self.total_time
        
    def step(self):
        """Run the simulation for one time step.

        The time step has already been specified as self.dt.

        Here we record any simulation values that we are tracing, send
        values from the simulation to the neural network inputs, step the
        neural network, take the neural network outputs and apply them to
        the simulation, and then step the simulation."""

        if self.lqr:
            self.applyLqrForce()
        elif self.network:
            self.applyNetworkForce()

        if self.regular_random_force and self.total_time > self.last_hit + 2.0:
            self.applyRandomForce()

        self.world.step(self.dt)
        self.total_time += self.dt
        log.debug('stepped world by %f time is %f', self.dt, self.total_time)
        log.debug('absolute value of angle is %f', abs(self.hinge_joint.getAngle()))
        
        if not self.finished:
            # set finished if the pole has fallen beyond pi/2
            if abs(self.hinge_joint.getAngle()) > math.pi/2 and self.max_simsecs != 0:
                log.debug('angle too high, simulation finished')
                self.finished = 1
            else:
                # nope, so increase our score
                self.score = self.total_time
                log.debug('current score is %f', self.score)

