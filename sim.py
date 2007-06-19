import math
import random
import logging

import ode
from cgkit.cgtypes import quat, mat3, mat4, vec3
from numpy import matrix
import bpg
import node
import network

CYLINDER_RADIUS = 1.0
CYLINDER_DENSITY = 1.0
MAX_UNROLLED_BODYPARTS = 20
SOFT_WORLD = 1
JOINT_MAXFORCE = 8.0 * CYLINDER_DENSITY * CYLINDER_RADIUS
HZ = 50
RELAX_TIME = 5.0

log = logging.getLogger('sim')
log.setLevel(logging.INFO)

class MyMotor(ode.AMotor):
    def __init__(self, world, jointgroup=None):
        ode.AMotor.__init__(self, world, jointgroup)
        self.desired_axisangle = [0.0, 0.0, 0.0]
        self.setParam(ode.ParamFMax, 0.0)
        self.setParam(ode.ParamFMax2, 0.0)
        self.setParam(ode.ParamFMax3, 0.0)
        self.old_angles = [0.0, 0.0, 0.0]

    def __del__(self):
        del self.joint

    def step(self):
        log.debug('MyMotor.step')

        x = self.getAngle(0) % (2*math.pi)
        y = self.getAngle(1) % (2*math.pi)
        z = self.getAngle(2) % (2*math.pi)
        dx = self.desired_axisangle[0] % (2*math.pi)
        dy = self.desired_axisangle[1] % (2*math.pi)
        dz = self.desired_axisangle[2] % (2*math.pi)
        log.debug('MyMotor angles=(%f,%f,%f) desired_angles=(%f,%f,%f)'%(x, y, z, dx, dy, dz))

        for (x, param) in (0, ode.ParamVel), (1, ode.ParamVel2), (2, ode.ParamVel3):
            a = self.getAngle(x)
            assert -math.pi <= a <= math.pi
            b = self.desired_axisangle[x]
            assert -math.pi <= b <= math.pi
            # go shortest way - figure out direction
            dist = abs(a-b)
            d = 1
            if a > b:
                d = -1
          # ignore axes that we don't control for each joint
            if type(self.joint) is ode.HingeJoint and x != 2 \
            or type(self.joint) is ode.UniversalJoint and x == 2:
                self.setParam(param, 0)
            else:
                # Proportional derivative controller. We have to estimate the
                # angular velocity because Motor.getAngleRate() is unimplemented
                # and joint.getAngleRate only works for HingeJoint
                ang_vel = abs(a - self.old_angles[x])*HZ
                self.old_angles[x] = a

                Kp = 10.0 # proportional constant
                Kd = 7.0 # derivative constant
                dv = Kp * dist - Kd * ang_vel
                dv = max(dv, 0)
                self.setParam(param, d*dv)

class Sim(object):
    "Simulation class, responsible for everything in the physical sim."

    def __init__(self, max_simsecs, gaussNoise):
        log.debug('Sim.__init__(max_simsecs=%s)', max_simsecs)
        # create world, set default gravity, geoms, flat ground, spaces etc.
        assert type(max_simsecs) is float or type(max_simsecs) is int
        self.total_time = 0.0
        self.relax_time = 0
        self.max_simsecs = float(max_simsecs)
        self.dt = 1.0/HZ
        self.world = ode.World()
        if SOFT_WORLD:
            self.world.setCFM(10**-6) # was 10**-3
            self.world.setERP(0.2) # was 0.1
        self.world.setGravity((0, 0, -9.8))
        self.space = ode.SimpleSpace()
        self.geoms = []
        self.ground = ode.GeomPlane(self.space, (0, 0, 1), 0)
        self.geoms.append(self.ground)
        self.score = 0.0
        self.finished = 0
        self.siglog = None
        self.bpgs = []
        self.contactGroup = ode.JointGroup()
        self.joints = []
        self.gaussNoise = gaussNoise
        self.points = []

    def __del__(self):
        log.debug('Sim.__del__()')
        if self.siglog:
            self.siglog.close()
        for j in self.joints:
            j.attach(None, None)
        for g in self.space:
            if g.placeable():
                g.setBody(None)
        # destroy hanging geoms
        ode._geom_c2py_lut.clear()
        del self.joints
        del self.space
        del self.geoms
        for bg in self.bpgs:
            bg.destroy()
        log.debug('/Sim.__del__()')

    def run(self):
        log.debug('Sim.run (secs=%f, dt=%f)', self.max_simsecs, self.dt)
        log.debug('num geoms = %d', self.space.getNumGeoms())
        while not self.finished:
            self.step()

    def handleCollide(self, args, geom1, geom2):
        """Callback function for the geometry collide() method

        Finds intersection points and calls self.addContact with each"""
        log.debug('handleCollide')
        # calculate intersection points
        cl = ode.collide(geom1, geom2)
        contacts = [c for c in cl if not (isinstance(c.getContactGeomParams()[3], ode.GeomCCylinder) and isinstance(c.getContactGeomParams()[4], ode.GeomCCylinder))]
        for c in contacts:
            assert c.getContactGeomParams()[1] == (0.0, 0.0, 1.0)
            log.debug('collision between %s and %s', str(geom1), str(geom2))
            self.addContact(geom1, geom2, c)
        log.debug('/handleCollide')

    def step(self):
        "Single step of sim. Sets self.finished when sim is over"
        log.debug('step')
        self.points = []
        self.space.collide(None, self.handleCollide)
        self.world.step(self.dt)
        self.contactGroup.empty()
        self.total_time += self.dt
        log.debug('stepped world by %f time is %f', self.dt, self.total_time)
        # check for sim blowing up
        for g in self.space:
            if g.placeable():
                v = vec3(g.getBody().getLinearVel())
                if v.length() > 150:
                    self.fail() # blew up, early exit
                    return
        nan = [g for g in self.space if g.placeable() for p in g.getPosition() if str(p)=='nan']
        if nan and self.max_simsecs != 0:
            self.fail()
        elif self.total_time > self.max_simsecs and self.max_simsecs != 0:
            self.finished = 1
        else:
            self.updateFitness()

class BpgSim(Sim):
    "Simulate articulated bodies built from BodyPartGraphs"

    def __init__(self, max_simsecs=30.0, fitnessName='meandistance', gaussNoise=0.01):
        Sim.__init__(self, max_simsecs, gaussNoise)
        log.debug('BPGSim.__init__')
        self.geom_contact = {}
        self.startpos = vec3(0, 0, 0)
        self.relaxed = 0
        self.prev_v = []
        fitnessMap = {
                'meandistance' : self.fitnessMeanDistance,
                'cumulativez' : self.fitnessCumulativeZ,
                'movement' : self.fitnessMovement,
                'walk' : self.fitnessWalk}
        if not fitnessName:
            fitnessName = 'meandistance'
        self.fitnessMethod = fitnessMap[fitnessName]
        self.relax_time = RELAX_TIME
        self.d = 0.0
        self.m = 0.0

    def getMaxSimTime(self):
        """max_simsecs attribute. add relax time to the sim time when set.
            return the real full sim time so that it can be rendered correctly."""
        return self.max_simsecs_value

    def setMaxSimTime(self, v):
        if v == 0:
            self.max_simsecs_value = 0
        else:
            self.max_simsecs_value = self.relax_time + v

    max_simsecs = property(getMaxSimTime, setMaxSimTime)

    def initSignalLog(self, fname):
        self.siglog = open(fname, 'w')
        assert self.bpgs
        s = '# time '
        self.signals = []
        for bg in self.bpgs:
            for bp in bg.bodyparts:
                bpi = bg.bodyparts.index(bp)
                for n in bp.network:
                    p = ''
                    if n in bp.network.inputs:
                        p = 'i'
                    if n in bp.network.outputs:
                        p = 'o'
                    l = 'bp%d-%d%s'%(bpi, bp.network.index(n), p)
                    s += '%s '%l
                    self.signals.append((bp,n))
                for m in bp.motors:
                    s += 'bp%d-M%c '%(bpi, m[-1])
                    self.signals.append((bp,m))
                axes = [ 'JOINT_%d'%j for j in bp.jointAxes ]
                for a in axes:
                    s += 'bp%d-J%c '%(bpi, a[-1])
                    self.signals.append((bp,a))
                s += 'bp%d-C '%(bpi)
                self.signals.append((bp, 'CONTACT'))
        s += '\n'
        self.siglog.write(s)

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
            bp.isRoot = 1
        else:
            # otherwise child scale is relative to parent
            bp.length = parent.length * bp.scale
            bp.isRoot = 0
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
        self.geoms.append(geom)
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
            c_v = j_v + rotmat * vec3(0, 0, bp.length/2.0)
            geom.setPosition(tuple(c_v))
            log.debug('set geom x,y,z = %f,%f,%f', c_v[0], c_v[1], c_v[2])

            jointclass = { 'hinge':ode.HingeJoint,
                           'universal':ode.UniversalJoint,
                           'ball':ode.BallJoint }
            j = jointclass[bp.joint](self.world)
            self.joints.append(j)
            # attach bodies to joint
            j.attach(parent.geom.getBody(), body)
            # set joint position
            j.setAnchor(j_v)
            geom.parent_joint = j

            # create motor and attach to this geom
            motor = MyMotor(self.world)
            self.joints.append(motor)
            motor.joint = j
            bp.motor = motor
            motor.attach(parent.geom.getBody(), body)
            motor.setMode(ode.AMotorEuler)

            # set joint axes
            maxforce = JOINT_MAXFORCE * bp.length * parent.length
            maxforce = 5000
            log.debug('motor maxforce = %f', maxforce)
            if bp.joint == 'hinge':
                # we have 3 points - parent body, joint, child body
                # find the normal to these points
                # (hinge only has 1 valid axis!)
                try:
                    axis1 = ((j_v-p_v).cross(j_v-c_v)).normalize()
                except ZeroDivisionError:
                    v = (j_v-p_v).cross(j_v-c_v)
                    v.z = 1**-10
                    axis1 = v.normalize()
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
                # (maybe this is only a problem in the test case with perfect axis alignment?)
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
        geom.child_joint_ends = set([ e.joint_end for e in bp.edges ])
        geom.parent_joint_end = joint_end
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

        for e in bp.edges:
            self.addBP(e.child, bp, e.joint_end)

    def add(self, bpgraph):
        """Add BodyPartGraph to simulation.
        Sim needs to convert into a simulatable object by:

          * Unroll bodypart graph
          * Create a graph of geoms
          * Each bp has a network"""

        log.debug('add(%s)', bpgraph)
        assert isinstance(bpgraph, bpg.BodyPartGraph)
        if not bpgraph.unrolled:
            bpgraph = bpgraph.unroll()
            bpgraph.connectInputNodes()
        bpgraph.sanityCheck()

        num_bps = len(bpgraph.bodyparts)
        log.debug('BPGSim.setSolution: number of unrolled bodyparts = %d', num_bps)

        assert bpgraph.root
        # recursively add all bodyparts
        self.addBP(bpgraph.root)
        self.raiseGeoms()
        # initialise the networks into random state
        for bp in bpgraph.bodyparts:
            bp.network.setState()
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

    def fitnessCumulativeZ(self):
        # fitness is mean z over bodies over time
        # per second
        total_z = 0.0
        count = 0
        for i in range(self.space.getNumGeoms()):
            geom = self.space.getGeom(i)
            if type(geom) is not ode.GeomPlane:
                (x, y, z) = geom.getPosition()
                total_z += z
                count += 1
        self.score += total_z/count*1/self.max_simsecs

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

    def fitnessMeanDistance(self):
        "Geometric distance from post-relax start position"
        mpos = self.meanPos(self.bpgs[0])
        self.score = (mpos - self.startpos).length()

    def fitnessMovement(self):
        "Cumulative movement between frames"
        bg = self.bpgs[0]
        for bp in bg.bodyparts:
            p = bp.geom.getPosition()
            if hasattr(bp, 'lastPos'):
                m = (vec3(p) - vec3(bp.lastPos)).length()
                d = ((self.meanPos(bg) - self.startpos).length())
                self.score += m + d/500
                self.m += m
                self.d += d / 500
            bp.lastPos = p

    def fitnessWalk(self):
        m = self.meanPos(self.bpgs[0])
        y = m[0]
        self.score = 0
        self.fitnessMovement()
        x = self.score
        if not hasattr(self,'cumx'):
            self.cumx = 0
        self.cumx += x
        z = len(self.bpgs[0].bodyparts)
        self.score = self.cumx/100 + 100*y + z

    def updateFitness(self):
        try:
            self.fitnessMethod()
        except OverflowError:
            self.fail()
        if type(self.score) not in [float, int]:
            log.critical('score is %s', self.score)
            assert type(self.score) in [float, int]

    def fail(self, reason='sim blew up'):
        self.score = -1
        self.finished = 1
        log.info('sim early exit - %s', reason)

    def relax(self):
        "Relax bpg until summed velocity over 2 seconds is less than some threshold."
        count = 0
        while 1:
            self.contactGroup.empty()
            self.space.collide(None, self.handleCollide)
            self.world.step(self.dt)
            # calc total linear velocity
            total = 0
            for g in self.space:
                if type(g) is not ode.GeomPlane:
                    b = g.getBody()
                    v = b.getLinearVel()
                    total += vec3(v).length()
            min_rt = HZ * 2 # min. relax time in frames
            if len(self.prev_v) < min_rt:
                self.prev_v += [total]
            else:
                self.prev_v = self.prev_v[1:] + [total]
                VELOCITY_THRESHOLD = 0.005
                # if total velocity for last min_rt frames less than threshold
                if sum(self.prev_v) < VELOCITY_THRESHOLD:
                    self.relaxed = 1
                    # recalc new start pos for fitness evals
                    self.startpos = self.meanPos(self.bpgs[0])
                    log.debug('relaxed - time=%f, startpos=%s, vt=%f', self.total_time, self.startpos, sum(self.prev_v))
                    break
            count += 1
            # if there are opposing violated constraints the body can move
            # constantly. We don't want that - we want the networks to
            # generate all of the movement energy. So we timeout after 10
            # seconds of waiting for the body to be still, and quit.
            if count > HZ * 10:
                return 1
        return 0

    def logSignals(self):
        if self.siglog:
            s = '%f '%self.total_time
            for (bp,n) in self.signals:
                if isinstance(n, node.Node):
                    s += '%f '%n.output
                elif n[0] == 'M':
                    mi = ord(n[-1]) - ord('0')
                    s += '%f '%bp.motor.desired_axisangle[mi]
                elif n[0] == 'J' or n[0] == 'C':
                    v = self.getSensorValue(bp, n)
                    s += '%f '%v
            self.siglog.write(s+'\n')
            self.siglog.flush()

    def addContact(self, geom1, geom2, c):
        # add a contact between a capped cylinder BP and the ground
        (cpos, cnor, cdep, cg1, cg2) = c.getContactGeomParams()
        # figure out which cylinder foot this contact describes
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
        ep1 = p + r*vec3(0, 0, length/2)
        # is cpos in sphere around ep0 or ep1?
        for ep in ep0, ep1:
            cpos = vec3(cpos)
            d2 = (cpos-ep).length()
            if (d2 <= radius**2*1.01):
                epc = ep
        # we will get two addContact() calls for each real contact, one for each
        # of the joined capped cylinders, so only add a contact for the
        # 'furthest out' from the root. If geom is the root then always add the
        # contact.
        if not cylinder.parent or epc == ep1:
            mu = 300
            self.points.append((cpos, (0,1,1), mu/1000.0))
            c.setMu(mu)
            j = ode.ContactJoint(self.world, self.contactGroup, c)
            j.attach(geom1.getBody(), geom2.getBody())
            # remember contact for touch sensors
            self.geom_contact[geom1] = 1
            self.geom_contact[geom2] = 1

    def getSensorValue(self, sbp, src):
        if isinstance(src, str) and src[0] == 'C':
            # sbp in contact with anything?
            value = self.geom_contact[sbp.geom]
        elif isinstance(src, str) and src[0] == 'J':
            # sbp joint angle
            if sbp.isRoot == 1:
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
            else:
                log.critical('bad sensor')
            # scale value to [0,1]
            value = (value/math.pi+1)/2
        elif isinstance(src, node.Node):
            # network output node, in domain [0,1]
            value = src.output

        assert 0 <= value <= 1

        # gaussian noise on sensors and motors
        noisyValue = random.gauss(value, self.gaussNoise)
        if noisyValue < 0: noisyValue = 0
        if noisyValue > 1: noisyValue = 1
        return noisyValue

    def step(self):
        """Sim loop needs to:

          * Go through all BodyParts, update all InputNodes with connected
            Sensor or OutputNode values.

          * Go through all BodyParts, and do a sync or async step
            of every Network.

          * Go through all BodyParts, for each motor, find connected
            OutputNode (if any) and get value."""

        if not self.relaxed:
            e = self.relax()
            if e:
                self.fail('relax')
                return

        self.logSignals()

        for g in self.geom_contact:
            self.geom_contact[g] = 0 # reset contact sensors

        # update sensor input values
        for bg in self.bpgs:
            for bp in bg.bodyparts:

                # send new values to motors
                if bp.joint == 'hinge':
                    motors = [2]
                elif bp.joint == 'universal':
                    motors = [0, 1]
                elif bp.joint == 'ball':
                    motors = [0, 1, 2]
                if hasattr(bp, 'motor') and bp.motor_input:
                    for mi in motors:
                        (sbp, src, weight) = bp.motor_input[mi]
                        v = self.getSensorValue(sbp, src)
                        assert 0 <= v <= 1
                        assert -7 <= weight <= 7
                        v = ((v-0.5)*2*weight/7)*math.pi # map to -pi..pi
                        assert -math.pi <= v <= math.pi
                        bp.motor.desired_axisangle[mi] = v

                # now do inputs to network
                for n in bp.network.inputs:
                    for (sbp, src) in n.externalInputs:
                        v = self.getSensorValue(sbp, src)
                        n.externalInputs[(sbp, src)] = v

            # step control networks and motors
            for bg in self.bpgs:
                bg.step()

        Sim.step(self)
        log.debug('/step')

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

    def __init__(self, max_simsecs=30, net=None, gaussNoise=0.01):
        """Creates the ODE and Geom bodies for this simulation"""
        Sim.__init__(self, max_simsecs, gaussNoise)
        log.debug('init PoleBalance sim')
        self.network = net

        CART_POSITION = (0, 0, 2)
        POLE_POSITION = (0, 0, 3+(5.0/2))
        CART_SIZE = (8, 8, 2)
        POLE_SIZE = (1, 1, 5)
        HINGE_POSITION = (0, 0, 3)
        CART_MASS = 10
        POLE_MASS = 0.5
        self.MAXF = 1000

        self.INIT_U = [] # initial force, eg [10000]

        self.cart_geom = ode.GeomBox(self.space, CART_SIZE)
        self.geoms.append(self.cart_geom)
        self.cart_body = ode.Body(self.world)
        self.cart_body.setPosition(CART_POSITION)
        cart_mass = ode.Mass()
        cart_mass.setBoxTotal(CART_MASS, CART_SIZE[0], CART_SIZE[1], CART_SIZE[2])
        self.cart_body.setMass(cart_mass)
        self.cart_geom.setBody(self.cart_body)

        self.pole_geom = ode.GeomBox(self.space, POLE_SIZE)
        self.geoms.append(self.pole_geom)
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
        self.joints.append(self.slider_joint)
        self.slider_joint.attach(self.cart_body, ode.environment)
        self.slider_joint.setAxis((1, 0, 0))
        self.slider_joint.setParam(ode.ParamLoStop, -5)
        self.slider_joint.setParam(ode.ParamHiStop, 5)

        # joint 1 - hinge between the two boxes
        self.hinge_joint = ode.HingeJoint(self.world)
        self.joints.append(self.hinge_joint)
        self.hinge_joint.attach(self.cart_body, self.pole_body)
        self.hinge_joint.setAnchor(HINGE_POSITION)
        self.hinge_joint.setAxis((0, 1, 0))

        self.last_hit = 0.0
        self.init_u_count = 0
        self.regular_random_force = 1
        self.lqr = None
        self.controlForce = 0
        self.randomForce = 0

    def setUseLqr(self):
        self.lqr = LqrController()

    def add(self, net):
        self.setNetwork(net)

    def setNetwork(self, net):
        """Tell PoleSim to use this network.

        Must have 1 input and 1 output"""

        assert type(net) is network.Network
        self.network = net
        self.network.setState()
        self.finished = 0
        # fake external_input connection so node knows its an input
        self.angleSignal = (None,'ANGLE_0', 1.0)
        for n in self.network:
            assert not n.externalInputs
        self.inputNode = self.network.inputs[0]
        self.inputNode.addExternalInput(self.angleSignal[0],self.angleSignal[1],self.angleSignal[2],)

    def setControlForce(self, f):
        f = min(self.MAXF, max(-self.MAXF, f))
        self.cart_body.addForce((f, 0, 0))
        self.controlForce = f

    def applyLqrForce(self):
        # construct state vector (x, xdot, theta, thetadot)
        state = matrix([[self.cart_body.getPosition()[0]],
                        [self.cart_body.getLinearVel()[0]],
                        [self.hinge_joint.getAngle()],
                        [self.hinge_joint.getAngleRate()]])
        # calculate and apply input force from LQR control matrix
        fx = self.lqr.calculateResponse(state)
        self.setControlForce(fx)

    def applyNetworkForce(self):
        angle = (self.hinge_joint.getAngle() + math.pi/4)/(math.pi/2)
        angle = random.gauss(angle, self.gaussNoise) # random noise
        angle = max(0, min(angle, 1)) # clip
        # send angle to network
        self.inputNode.externalInputs[(self.angleSignal[0],self.angleSignal[1])] = angle
        self.network.step()
        # read network, get desired force/velocity
        v = self.network.outputs[0].output
        v = random.gauss(v, self.gaussNoise)
        v = (v-0.5) * self.MAXF # map [0,1] -> [-25,25]
        self.slider_joint.setParam(ode.ParamVel, v)
        self.setControlForce(v)

    def applyRandomForce(self):
        # hit the pole with a random force weighted by time
        f = (random.random() - 0.5) * self.total_time**2
        f *= 100
        self.randomForce = f
        self.pole_body.addForce((f, 0, 0))
        self.last_hit = self.total_time

    def updateFitness(self):
        self.score = self.total_time
        log.debug('current score is %f', self.score)

    def step(self):
        """Run the simulation for one time step.

        The time step has already been specified as self.dt.

        Here we record any simulation values that we are tracing, send
        values from the simulation to the neural network inputs, step the
        neural network, take the neural network outputs and apply them to
        the simulation, and then step the simulation."""

        self.logSignals()

        if self.lqr:
            self.applyLqrForce()
        elif self.network:
            self.applyNetworkForce()

        # initial force vector
        if self.init_u_count < len(self.INIT_U):
            f = self.INIT_U[self.init_u_count]
            self.cart_body.addForce((f, 0, 0))
            self.init_u_count += 1

        # regular random force
        if self.regular_random_force and self.total_time > self.last_hit + 2.0:
            self.applyRandomForce()

        log.debug('absolute value of angle is %f', abs(self.hinge_joint.getAngle()))

        # set finished if the pole has fallen beyond pi/2
        if not self.finished and abs(self.hinge_joint.getAngle()) > math.pi/2 and self.max_simsecs != 0:
                log.debug('angle too high, simulation finished')
                self.finished = 1

        Sim.step(self)

    def run(self):
        Sim.run(self)
        if self.network:
            # hack, setNetwork adds an external input, so we remove it here
            self.inputNode.removeExternalInput(self.angleSignal[0],self.angleSignal[1])

    def initSignalLog(self, fname):
        self.siglog = open(fname, 'w')
        s = '# time angle randf ctrlf '
        if self.network:
            for n in self.network:
                s += 'n%d'%(self.network.index(n))
                if n in self.network.inputs:
                    s += 'i'
                if n in self.network.outputs:
                    s += 'o'
                s += ' '
        s += '\n'
        self.siglog.write(s)

    def logSignals(self):
        if self.siglog:
            s = '%f %f %f %f '%(self.total_time, self.hinge_joint.getAngle(), self.randomForce, self.controlForce)
            if self.network:
                for n in self.network:
                    s += '%f'%n.output
                    if self.network.index(n) != len(self.network)-1:
                        s += ' '
            self.siglog.write(s+'\n')
            self.siglog.flush()
