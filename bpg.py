"bpg.py - this file holds all classes necessary for body part graphs."

import random
import copy
import math
import os

from persistent import Persistent
from persistent.list import PersistentList
from persistent.dict import PersistentDict
import logging

from ode import Infinity
from cgkit.cgtypes import vec3
import network
import node

BPG_MAX_NODES = 4
BPG_MAX_EDGES = 6
BP_MAX_RECURSIVE_LIMIT = 2
BP_MIN_LENGTH = 3
BP_MAX_LENGTH = 10
BPG_MIN_UNROLLED_BODYPARTS = 5

log = logging.getLogger('bpg')
log.setLevel(logging.INFO)

class Edge(Persistent):
    """Edge to child bodypart.

    child is the target bodypart.

    joint_end is -1 or 1 and indicates whether the child is attached to
    the left (-1) or right (1) of the bodypart cylinder."""
    def __init__(self, child, joint_end, terminal_only):
        self.child = child
        self.joint_end = joint_end
        self.terminal_only = terminal_only
    def __repr__(self):
        return 'Edge(child=%s, joint_end=%d, terminal_only=%d)'%(self.child, self.joint_end, self.terminal_only)

def unroll_bodypart_copy(bp_o):
    "return a copy of bp_o, without edges"
    # shallow copy first
    bp_c = copy.copy(bp_o)
    # now replace anything that we can't share or don't want
    bp_c.network = copy.deepcopy(bp_o.network)
    bp_c.edges = PersistentList()
    bp_c.input_map = None
    bp_c.motor_input = PersistentList([None,None,None])
    bp_c._v_instance_count = bp_o._v_instance_count
    assert bp_c._v_instance_count != None
    bp_c.genotype = bp_o
    return bp_c

def unroll_bodyparts(bp_o, bpg_c, bp_c):
    """bp_o -- original bodypart, we already copied this so consider its children
    bpg_c -- new graph, for adding new bodyparts to
    bp_c -- copy of bp_o (ie. parent of any copies we make)"""
    log.debug('%s has %s edges: %s', bp_o, len(bp_o.edges), bp_o.edges)
    for e in bp_o.edges:
        # whether we follow edge depends on our bp instance count and
        # whether or not the edge is terminal, and also on whether the
        # child has reached its recursive limit
        if ((bp_o._v_instance_count < bp_o.recursive_limit and not e.terminal_only) \
            or ((bp_o._v_instance_count == bp_o.recursive_limit) and e.terminal_only)) \
            and e.child._v_instance_count < e.child.recursive_limit:
            # copy the child bodypart
            child_bp_c = unroll_bodypart_copy(e.child)
            e.child._v_instance_count += 1
            # add it to the copied bpg
            bpg_c.bodyparts.append(child_bp_c)
            # add it as a child to the copy bodypart. copy the edge.
            e_c = Edge(child_bp_c, e.joint_end, e.terminal_only)
            bp_c.edges.append(e_c)
            # recurse
            unroll_bodyparts(e.child, bpg_c, child_bp_c)
            # restore instance count
            e.child._v_instance_count -= 1
        else:
            log.debug('didnt follow edge %s', e)
            b = bp_o._v_instance_count < bp_o.recursive_limit and not e.terminal_only
            log.debug('bp_o._v_instance_count < bp_o.recursive_limit and not e.terminal_only: %d', b)
            b = (bp_o._v_instance_count == bp_o.recursive_limit) and e.terminal_only
            log.debug('(terminal or (bp_o._v_instance_count == bp_o.recursive_limit)) and e.terminal_only: %d', b)
            b = e.child._v_instance_count < e.child.recursive_limit
            log.debug('e.child._v_instance_count < e.child.recursive_limit: %d', b)

def unroll_bodypart(bp_o):
    "bp_o -- root BodyPart original."
    bpg_c = BodyPartGraph()
    if bp_o:
        # ignore rules.. we may as well always have a root bodypart if theres something there
        bp_c = unroll_bodypart_copy(bp_o)
        bp_o._v_instance_count += 1
        assert bp_c
        bpg_c.root = bp_c
        bpg_c.bodyparts.append(bp_c)
        log.debug('unroll: added root bp')
        unroll_bodyparts(bp_o, bpg_c, bp_c)
        bp_o._v_instance_count -= 1
    else:
        log.warn('unroll_bodypart: empty bpg')
    return bpg_c

def randomVec3():
    "Create a random normalised vector"
    try:
        v = vec3(random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1)).normalize()
    except:
        v = vec3(1,0,0)
    return v

def randomQuat():
    "Create a random quaternion (vector and angle)"
    radians = random.uniform(0, 2*math.pi)
    v = randomVec3()
    return (radians, tuple(v))

class BodyPart(Persistent):
    """Part of the articulated body. Geometry is a capped cylinder.

    Attributes:

    length - Absolute length of cylinder.
    rotation - Absolute rotation specified as rotation about a vector (radians, (x,y,z))
    scale - The length is specified as a scale relative to the parent. Scale
      can be [-2..2]. Even the root node has a scale, so that it can be used in loops.
    recursive_limit - How many times this BodyPart can be used to generate a phenotype part when in a recursive cycle.
    edges - List of outgoing Edges containing BodyPart, joint point [0|1], terminal_only [0|1].
    network - Each unrolled BodyPart has its own network to control it.
    input_map - This is a hash. Each target (input node or motor) has an entry here which points to a list (nodes or sensor string) which is ordered by priority.
    """

    def __init__(self, network_args):
        """Randomly create a body part"""
        log.debug('BodyPart.__init__')
        self.network = network.Network(**dict(network_args))
        self.edges = PersistentList()
        self.input_map = PersistentDict()
        # call mutate() to create evolvable attributes
        self.mutations = 0
        self.mutate(1)
        self.motor_input = PersistentList([None,None,None])
        
    def destroy(self):
        self.network.destroy()
        del self.edges
        del self.input_map
        del self.motor_input

    def connectTo(self, child):
        "Make an edge from this bodypart to a child"
        log.debug('BodyPart.connectTo')
        # random connection
        joint_end = random.choice([-1,1])
        term_only = random.choice([0,1])
        edge = Edge(child, joint_end, term_only)
        self.edges.append(edge)

    def mutate(self, p):
        "Mutate BodyPart parameters with probability p"
        attrs = { 
            'scale' : 'random.uniform(0.2, 5.0)',
            'recursive_limit' : 'random.randint(0, BP_MAX_RECURSIVE_LIMIT)',
            'joint' : "random.choice(['hinge','universal','ball'])",
            'axis1' : 'tuple(vec3(random.uniform(-1,1), random.uniform(-1,1), 0).normalize())',
            'axis2' : 'tuple(vec3((0,0,1)).cross(vec3(self.axis1)))',
            'ball_rot' : 'randomQuat()',
            'rotation' : 'randomQuat()',
            'lostop' : 'random.choice([-Infinity, random.uniform(0, -math.pi)])',
            # axis1 angle must be in -pi/2..pi/2 to avoid a singularity in ode
            'lostop2' : 'random.uniform(0, -math.pi/2)',
            'lostop3' : 'random.choice([-Infinity, random.uniform(0, -math.pi)])',
            'histop' : 'random.choice([Infinity, random.uniform(0, math.pi)])',
            'histop2' : 'random.uniform(0, math.pi/2)',
            'histop3' : 'random.choice([Infinity, random.uniform(0, math.pi)])',
            'friction_left' : 'random.uniform(0, 1000)',
            'friction_right' : 'random.uniform(0, 1000)'
            }
        
        mutations = 0
        for attr in attrs:
            if random.random() < p:
                setattr(self, attr, eval(attrs[attr]))
                mutations += 1
        # we need to force recalc of axis2 if axis1 changed
        self.axis2 = eval(attrs['axis2'])
        # ensure stop2 is valid to avoid singularity
        if self.lostop2 > self.histop2:
            t = self.lostop2
            self.lostop2 = self.histop2
            self.histop2 = t
        # mutate control network
        if p:
            self.mutations += self.network.mutate(p)
        return mutations

class BodyPartGraph(Persistent):
    """A collection of BodyParts joined by edges."""
    def __init__(self, network_args=None):
        """if network_args is None create empty BPG else create a
        random BPG."""

        log.debug('BodyPartGraph.__init__')
        self.bodyparts = PersistentList()
        self.unrolled = 0
        if not network_args:
            # this is used for unrolled bodypart copies
            self.root = None
        else:
            while 1:
                self.randomInit(network_args)
                u = self.unroll()
                if len(u.bodyparts) >= BPG_MIN_UNROLLED_BODYPARTS:
                    break
                
    def destroy(self):
        for bp in self.bodyparts:
            bp.destroy()
            
    def step(self):
        for bp in self.bodyparts:
            bp.network.step()
        for bp in self.bodyparts:
            if hasattr(bp, 'motor'):
                bp.motor.step()
                
    def randomInit(self, network_args):
        # create graph randomly
        del self.bodyparts[:]
        num_bodyparts = random.randint(2, BPG_MAX_NODES)
        log.debug('Creating %d random BodyParts'%(num_bodyparts))
        for _ in range(num_bodyparts):
            bp = BodyPart(network_args)
            self.bodyparts.append(bp)
        # randomly select the root node
        self.root = random.choice(self.bodyparts)
        root_index = self.bodyparts.index(self.root)
        # possible n^2 connections
        num_connects = random.randint(1, BPG_MAX_EDGES)
        log.debug('creating upto %d random connections', num_connects)
        # Now select randomly and use to create actual connect
        inset = [root_index]
        outset = range(0,root_index) + range(root_index+1, num_bodyparts)
        for _ in range(num_connects):
            # select from inset
            src_i = random.randint(0, len(inset)-1)
            if not outset:
                break
            inoutset = inset + outset
            dst_i = random.randint(0, len(inoutset)-1)
            src = self.bodyparts[inset[src_i]]
            bodyparts_dst_i = inoutset[dst_i]
            dst = self.bodyparts[bodyparts_dst_i]
            src.connectTo(dst)
            # there is no check for an existing edge, so we can get multiple edges between src and dst
            if not bodyparts_dst_i in inset:
                inset.append(bodyparts_dst_i)
            if bodyparts_dst_i in outset:
                outset.remove(bodyparts_dst_i)
        self.connectInputNodes()
        for bp in self.bodyparts:
            for i in 0,1,2:
                assert not bp.motor_input[i]
        self.sanityCheck()

    def getNeighbours(self, bp):
        """Calculate the set of valid neighbour bodyparts of bp
        
        A bodypart is a neighbour of bp if it is a parent or child in the
        bodypartgraph, or if it is bp itself."""
        assert bp in self.bodyparts
        # find possible sources for connection in this phenotype
        valid_bp_neighbours = [bp]
        # .. all children
        valid_bp_neighbours += [ e.child for e in bp.edges ]
        # .. parent
        valid_bp_neighbours += [ p for p in self.bodyparts for e in p.edges if e.child == bp ]
        for neighbour in valid_bp_neighbours:
            assert neighbour in self.bodyparts
        log.debug('valid bp neighbours = %s', valid_bp_neighbours)
        return valid_bp_neighbours

    def connectInputNodes(self, sanitycheck=1):
        """Connect all sensory input nodes up to something.
        
        If the bpg is already unrolled, then it is a phenotype and the results
        won't be backannotated to the genotype input_map. If anything is left
        unconnected, an assert error will be thrown.

        If the bpg isn't already unrolled, then it will be, and any missing
        connections will be randomly selected and backannotated into the
        genotype input_map, so that later calls to unroll and connect will be
        able to succeed in connecting every input node up.        
        """
        log.debug('BodyPartGraph.connectInputNodes(self=%s)', self)
        if self.unrolled:
            log.debug('self.unrolled=1')
            backannotate = 0
            p_bpg = self
        else:
            log.debug('self.unrolled=0')
            backannotate = 1
            p_bpg = self.unroll()
        for bp in p_bpg.bodyparts:
            for i in 0,1,2:
                if bp.motor_input[i]:
                    (b,s) = bp.motor_input[i]
                    assert b in p_bpg.bodyparts
        log.debug('p_bpg=%s (bodyparts=%s)'%(p_bpg, p_bpg.bodyparts))
        backannotate=1
        # find all unconnected nodes/motors
        for bp in p_bpg.bodyparts:
            for n in bp.network:
                assert not n.deleted
        un = set([ (p_bp, p_signal) for p_bp in p_bpg.bodyparts for p_signal in p_bp.network.inputs if not p_signal.external_input ])
        un = un.union(set([ (p_bp, 'MOTOR_%d'%i) for p_bp in p_bpg.bodyparts for i in 0,1,2 if not p_bp.motor_input[i] ]))

        for (p_bp, p_signal) in un:
            # find corresponding genotype of this node/motor
            g_bp = p_bp.genotype
            if isinstance(p_signal, node.Node):
                g_signal = g_bp.network[p_bp.network.index(p_signal)]
                assert g_signal in g_bp.network.inputs
            else:
                g_signal = p_signal
            # is there an entry in g_bp.input_map for the target node/motor? 
            p_neighbours = p_bpg.getNeighbours(p_bp)
            if not g_bp.input_map.has_key(g_signal):
                g_bp.input_map[g_signal] = PersistentList()
            # are there matching maps for this phenotype topology?
            m = [ (g_src_bp, g_src_signal, p_src_bp) for (g_src_bp, g_src_signal) in g_bp.input_map[g_signal] for p_src_bp in p_neighbours if p_src_bp.genotype is g_src_bp]

            if m:
                # yes. use the first one to connect the node/motor.
                (g_src_bp, g_src_signal, p_src_bp) = m[0]
                if isinstance(g_src_signal, node.Node):
                    # find phenotype Node
                    node_index = g_src_bp.network.index(g_src_signal)
                    p_node = p_src_bp.network[node_index]
                    # set source to a phenotype (bp,s)
                    p_source = (p_src_bp, p_node)
                else:
                    p_source = (p_src_bp, g_src_signal)

            else:
                # no entry in input_map for this node/motor
                # raise error if we aren't connecting up a genotype bpg
                assert backannotate
                # pick a random (bp, signal) from p_bp and backannotate into g_bp.input_map
                p_src_bp = random.choice(p_neighbours)
                p_src_signal = random.choice(p_src_bp.network.outputs+['CONTACT', 'JOINT_0', 'JOINT_1', 'JOINT_2'])
                p_source = (p_src_bp, p_src_signal)

                # find genotype of the chosen phenotype (bp,s)
                g_src_bp = p_src_bp.genotype
                if isinstance(p_src_signal, node.Node):
                    # phenotype output node -> genotype output node 
                    # (depends on offsets being the same)
                    g_src_signal = g_src_bp.network[p_src_bp.network.index(p_src_signal)]
                    genosource = (g_src_bp, g_src_signal)
                else:
                    genosource = (g_src_bp, p_src_signal)

                log.debug('entering %s -> %s into bp.input_map', genosource, g_signal)
                # add to genotype.input_map our backannotated source
                g_bp.input_map[g_signal].append(genosource)
                assert g_bp in [ pbp.genotype for pbp in p_bpg.bodyparts ]

            # add to signal target.
            if isinstance(p_signal, node.Node):
                assert not p_signal.external_input
                p_signal.external_input = p_source
            elif p_signal[:6] == 'MOTOR_':
                i = ord(p_signal[6])-ord('0')
                assert not p_bp.motor_input[i]
                (sbp, ssig) = p_source
                log.debug('p_bp.motor_input[%d]=(%s,%s)'%(i,sbp,ssig))
                assert sbp in p_bpg.bodyparts
                p_bp.motor_input[i] = p_source

        for bp in p_bpg.bodyparts:
            for i in 0,1,2:
                (b,s) = bp.motor_input[i]
                log.debug('p_bpg.bodyparts[%d].motor_input[%d]=(%s,%s)'%(p_bpg.bodyparts.index(bp),i,b,s))
                assert b in p_bpg.bodyparts
        if sanitycheck:
            p_bpg.sanityCheck()

        log.debug('/BodyPartGraph.connectInputNodes')

    def dot(self, filename, s):
        "Write string s to a file and run dot"
        view = 0
        if filename:
            if filename == '-':
                view = 1
                filename = 'tmp.pdf'
            (fbase, ext) = os.path.splitext(filename)
            ext = ext[1:]
            f = open(fbase+'.dot', 'w')
            f.write(s)
            f.close()
            if ext != 'dot':
                if ext == 'pdf':
                    os.system('dot -Tps -o%s.eps %s.dot'%(fbase, fbase))
                    os.system('epstopdf %s.eps %s.pdf'%(fbase, fbase))
                    os.remove(fbase+'.eps')
                else:
                    os.system('dot -T%s -o%s.%s %s.dot'%(ext, fbase, ext, fbase))
                    os.remove(fbase+'.dot')
            if view:
                os.system('kpdf tmp.pdf')

    def getInputs(self, bp):
        """Return a list of all the external inputs to bodypart bp.
        
        Returns: [ (targetbp, (srcbp, signal)), ... ]"""

        if self.unrolled:
            sources = [ (neuron, neuron.external_input) for neuron in bp.network.inputs ]
            if bp.joint == 'hinge':
                sources += [ ('MOTOR_2', bp.motor_input[2]) ]
            if bp.joint in [ 'universal', 'ball' ]:
                sources += [ ('MOTOR_0', bp.motor_input[0]) ]
                sources += [ ('MOTOR_1', bp.motor_input[1]) ]
            if bp.joint == 'ball':
                sources += [ ('MOTOR_2', bp.motor_input[2]) ]
        else:
            sources = [ (neuron, src) for neuron in bp.input_map for src in bp.input_map[neuron] ]

        return sources

    def plotNetworks(self, filename, toponly):
        "Plot a graph with the interconnected networks of each bodypart"
        log.debug('plotNetworks(%s,%s)', filename, toponly)
        self.sanityCheck()

        s = 'digraph G {\n compound=true\n'
        for i in range(len(self.bodyparts)):
            s += ' subgraph cluster%d {\n'%i
            s += '  label = "bp%d"\n'%i
            bp = self.bodyparts[i]
            prefix = 'bp%d_'%i
            s += bp.network.plotNodes(toponly, prefix)
            s += bp.network.plotEdges(toponly, prefix)
            if bp.joint == 'hinge':
                motors = ['MOTOR_2']
            elif bp.joint == 'universal':
                motors = ['MOTOR_0', 'MOTOR_1']
            elif bp.joint == 'ball':
                motors = ['MOTOR_0', 'MOTOR_1', 'MOTOR_2']
            signals = ['CONTACT', 'JOINT_0', 'JOINT_1', 'JOINT_2']

            for signal in signals + motors:
                if toponly:
                    s += '  %s%s [shape=point]\n'%(prefix, signal)
                else:
                    style = ''
                    s += '  %s%s [label="%s"%s]\n'%(prefix, signal, signal, style)
            s += ' }\n'

        # plot inter-bodypart (node.external_input) edges here
        for bp in self.bodyparts:
            sources = self.getInputs(bp)
            for (tsignal, (sbp, signal)) in sources:
                sbp_i = self.bodyparts.index(sbp)
                tbp_i = self.bodyparts.index(bp)
                if isinstance(tsignal, node.Node):
                    tn_i = bp.network.index(tsignal)
                    ts = '%d'%tn_i
                else:
                    ts = str(tsignal)
                if type(signal) is str:
                    s += ' bp%d_%s -> bp%d_%s\n'%(sbp_i, signal, tbp_i, ts)
                else: # node
                    s += ' bp%d_%d -> bp%d_%s\n'%(sbp_i, sbp.network.index(signal), tbp_i, ts)

        # plot bpg topology
        for i in range(len(self.bodyparts)):
            targets = [ e.child for e in self.bodyparts[i].edges ]
            for t in targets:
                ti = self.bodyparts.index(t)
                s += ' bp%d_0 -> bp%d_0 [ltail=cluster%d, lhead=cluster%d, color=red]\n'%(i, ti, i, ti)

        s += '}'

        self.dot(filename, s)
        return s

    def plotBpg(self, filename=None, toponly=0):
        "Dump this BodyPartGraph to a graphviz dot string/file"
        log.debug('BodyPartGraph.plot')
        self.sanityCheck()

        s = 'digraph G {\n'
        # first dump all of the nodes with labels
        for i in range(len(self.bodyparts)):
            bp = self.bodyparts[i]
            label = 'bp%d'%(i)
            if not toponly:
                label += ' (scale=%.2f,' % (bp.scale)
                label += 'rec_lim=%d,' % (bp.recursive_limit)
                label += 'joint=%s,' % (bp.joint)
                label += 'net.inputs=%d)' % (len(bp.network.inputs))
            s += ' '*4 + 'n%d [label="%s"]\n' % (i,label)
        s += '\n'
        # now dump all of the edges with labels
        for i in range(len(self.bodyparts)):
            bp = self.bodyparts[i]
            # plot all edges to children
            for edge in bp.edges:
                child_index = self.bodyparts.index(edge.child)
                label = ''
                if not toponly:
                    label += 'joint_end=%d,terminal_only=%d' % (edge.joint_end, edge.terminal_only)
                s += ' '*4 + 'n%d -> n%d [label="%s"]\n' % (i, child_index, label)
            # plot all incoming sensory edges
            sources = self.getInputs(bp)
            for (tsignal, (sbp, ssignal)) in sources:
                if toponly:
                    label = ''
                else:
                    if isinstance(ssignal, str):
                        slabel = ssignal
                    else:
                        slabel = 'bp%d-%d'%(self.bodyparts.index(sbp), sbp.network.index(ssignal))
                    if isinstance(tsignal, str):
                        tlabel = tsignal
                    else:
                        tlabel = 'bp%d-%d'%(i, bp.network.index(tsignal))
                    label = '%s -> %s'%(slabel, tlabel)
                # edge between 2 bps labelled with signal source
                s += ' '*4 + 'n%d -> n%d [style=dashed, label="%s"]\n' % (self.bodyparts.index(sbp), i, label)
        s += '}'

        self.dot(filename, s)
        # return graph as a string
        return s

    def unroll(self):
        """Returns new BPG, of possibly 0 size.

        The BPG will be unrolled. Each path through the network will
        be traced, and a new cloned body part is made for each
        original. The connectivity of the copy will be the same as the
        original, except the copy will respect upper limits on the
        number of instances of any given body part in a single path,
        and final copy instances of a part will be connected to 'final
        edge' children. No loops are left in the new BPG."""
        log.debug('BodyPartGraph.unroll')
        # we need a count of every bp to make sure we don't loop too many times
        for b in self.bodyparts:
            b._v_instance_count = 0
        for b in self.bodyparts:
            assert b._v_instance_count == 0
        bpg = unroll_bodypart(self.root)
        bpg.unrolled = 1
        log.debug('/BodyPartGraph.unroll (bpg size %d -> size %d)', len(self.bodyparts), len(bpg.bodyparts))
        return bpg

    def sanityCheck(self):
        "See if anything is wrong with this BodyPartGraph"
        log.debug('BodyPartGraph.sanityCheck')
        # check everything we can reach from the root is in our bodypart list
        assert self.root in self.bodyparts
        bps = [self.root]
        reachable = bps
        while bps:
            bp = bps[0]
            if bp in reachable:
                # already found
                del bps[0]
            else:
                reachable.append(bp)
                assert self.bodyparts.count(bp) == 1
                #assert bp._v_instance_count >= 0
                for e in bp.edges:
                    assert self.bodyparts.count(e.child) == 1
                    if e.child not in reachable:
                        bps.append(e.child)

        # check every target child is in our bodyparts list
        for i in range(len(self.bodyparts)):
            bp = self.bodyparts[i]
            for e in bp.edges:
                assert self.bodyparts.count(e.child) == 1

        # make sure that everything is connected
        if self.unrolled:
            phen_bpg = self
        else:
            phen_bpg = self.unroll()
        phen_bpg.connectInputNodes(sanitycheck=0)
        # all external inputs should have a single connection, otherwise it
        # should be None
        for bp in phen_bpg.bodyparts:
            for n in bp.network:
                if n in bp.network.inputs:
                    assert n.external_input
                    (sbp, src) = n.external_input
                    assert sbp in phen_bpg.bodyparts
                    if isinstance(src, node.Node):
                        assert src in sbp.network.outputs
                else:
                     assert not n.external_input
            # check motor connections
            for i in 0,1,2:
                assert bp.motor_input[i]
                (sbp, src) = bp.motor_input[i]
                assert sbp in phen_bpg.bodyparts
                if isinstance(src, node.Node):
                    assert src in sbp.network.outputs
        for bp in self.bodyparts:
            if self.unrolled:
                # we only use input maps for the genotype, since phenotype BPs
                # link back to their genotype BPs anyway
                assert not bp.input_map
            else:
                # Make sure all entries in input_map are valid bodyparts and neurons
                for (tsignal, srclist) in bp.input_map.items():
                    assert tsignal in bp.network.inputs or tsignal[:5] == 'MOTOR'
                    for (sbp, ssignal) in srclist:
                        assert sbp in self.bodyparts
                        if isinstance(ssignal, node.Node):
                            assert ssignal in sbp.network
                        else:
                            assert ssignal in ['JOINT_0', 'JOINT_1', 'JOINT_2', 'CONTACT']

    def fixup(self):
        """Fix any problems with this BodyPartGraph (ie. invalid connections,
        bad root, etc.) This is called on rolled bpgs after mutation, and
        unrolled after modification to fit simulation constraints (eg.
        MAX_UNROLLED_BODYPARTS).  """
        # remove edges that point to invalid children
        for bp in self.bodyparts:
            edges_to_remove = []
            for e in bp.edges:
                if e.child not in self.bodyparts:
                    #bp.edges.remove(e)
                    edges_to_remove.append(e)
            for e in edges_to_remove:
                bp.edges.remove(e)
        # make sure root exists
        if self.root not in self.bodyparts:
            # randomly select the root node
            self.root = random.choice(self.bodyparts)
        # remove input_map entries that are invalid
        for bp in self.bodyparts:
            if bp.input_map:
                # we need to keep a list and erase at the end otherwise we fall into
                # the trap of removing items for a mutable list whilst iterating
                # over it
                for (tneuron, srclist) in bp.input_map.items():
                    if tneuron not in bp.network.inputs:
                        del bp.input_map[tneuron]
                    else:
                        for (sbp, sneuron) in srclist[:]:
                            if sbp not in self.bodyparts or sneuron not in sbp.network:
                                srclist.remove((sbp, sneuron))
        for bp in self.bodyparts:
            if bp.input_map:
                for (tneuron, srclist) in bp.input_map.items():
                    for (sbp, sneuron) in srclist:
                        assert sbp in self.bodyparts

        # check whether input_map entries are still valid
        for bp in self.bodyparts:
            krm = []
            for k in bp.input_map.keys():
                if k not in self.bodyparts:
                    krm.append(k)
                else:
                    # key is valid
                    toremove = []
                    for (sbp, sig) in bp.input_map[k]:
                        # check sbp is ok and src is a string or output node
                        if sbp not in self.bodyparts or (isinstance(sig, node.Node) and sig not in sbp.network.outputs):
                            toremove.append((sbp, sig))
                    for x in toremove:
                        bp.input_map[k].remove(x)
            for k in krm:
                del bp.input_map[k]

        # fix input_map so all input nodes are connected
        self.connectInputNodes()
        self.sanityCheck()

    def mutate_delete_edges(self, p):
        "Randomly erase edges in this BodyPartGraph with probability p"
        for bp in self.bodyparts:
            for i in range(len(bp.edges)-1, -1, -1):
                if random.random() < p:
                    # delete edge
                    log.debug('delete edge')
                    self.mutations += 1
                    del bp.edges[i]
                    self.fixup()
                    self.sanityCheck()

    def mutate_add_edges(self, p):
        "Randomly add edges in this BodyPartGraph with probability p"
        for s_bp in self.bodyparts:
            if random.random() < p:
                #and len(self.bodyparts) < BPG_MAX_EDGES:
                # add edge
                log.debug('add edge')
                self.mutations += 1
                t_bp = random.choice(self.bodyparts)
                e = Edge(t_bp, random.choice([-1,1]), random.choice([0,1]))
                s_bp.edges.append(e)
                # we now have new nodes in the unrolled bpg which don't have
                # entries in their genotype bp for their neighbours, so fixup
                self.fixup()
                self.sanityCheck()
        
    def mutate_delete_nodes(self, p):
        "Randomly delete nodes in this BodyPartGraph with probability p"
        for i in range(len(self.bodyparts)-1, -1, -1):
            if random.random() < p and len(self.bodyparts) > 1:
                # delete node
                log.debug('delete node')
                self.mutations += 1
                bp_del = self.bodyparts[i]
                # delete all edges pointing to this node
                for bp in self.bodyparts:
                    edges_to_remove = []
                    for e in bp.edges:
                        if e.child == bp_del:
                            edges_to_remove.append(e)
                    for e in edges_to_remove:
                        bp.edges.remove(e)
                self.bodyparts.remove(bp_del)
                if bp_del == self.root:
                    self.root = random.choice(self.bodyparts)
                self.fixup()
                self.sanityCheck()

    def mutate_copy_nodes(self, p):
        "Randomly copy nodes in this BodyPartGraph with probability p"
        for i in range(len(self.bodyparts)):
            if random.random() < p and len(self.bodyparts) < BPG_MAX_NODES:
                # copy and mutate node
                log.debug('copy node')
                self.mutations += 1
                c = copy.deepcopy(self.bodyparts[i])
                # we did in fact just copy everything the bp links to ...
                # fixme: correct? yes? efficient? probably not.
                c.edges = PersistentList()
                c.mutate(p)
                self.bodyparts.append(c)

                # random incoming edges
                i = random.randint(1, len(self.bodyparts)/2)
                for _ in range(i):
                    # add edges
                    e = Edge(c, random.choice([-1,1]), random.choice([0,1]))
                    s_bp = random.choice(self.bodyparts)
                    s_bp.edges.append(e)

                # random outgoing edges
                i = random.randint(1, len(self.bodyparts)/2)
                for _ in range(i):
                    # add edges
                    t_bp = random.choice(self.bodyparts)
                    e = Edge(t_bp, random.choice([-1,1]), random.choice([0,1]))
                    c.edges.append(e)
                self.fixup()
                self.sanityCheck()

    def mutate_inputmaps(self, p):
        "Randomly rewire input_maps in each BodyPart with probability p"
        for bp in self.bodyparts:
            for _ in range(len(bp.input_map)):
                if random.random() < p:
                    log.debug('mutate input_map')
                    self.mutations += 1
                    di = random.choice(bp.input_map.keys())
                    del bp.input_map[di]
        self.connectInputNodes()
        self.sanityCheck()
        
    def mutate(self, p):
        "Mutate the BodyPartGraph nodes, edges, and all parameters."
        log.debug('bpg.mutate(p=%f)', p)

        self.sanityCheck()
        self.mutations = 0
        self.mutate_delete_edges(p)
        self.mutate_add_edges(p)
        self.mutate_delete_nodes(p)
        self.mutate_copy_nodes(p)
        self.mutate_inputmaps(p)

        # FIXME: mutate number of input and output nodes
        # mutate motors and sensors?
        self.sanityCheck()
        for bp in self.bodyparts:
            # mutate individual parameters
            self.mutations += bp.mutate(p)
            # since bp mutate can change the topology of the unrolled graph via
            # recursive_limit, we need to fix up external_input and maybe others
            self.fixup()
            self.sanityCheck()

        self.sanityCheck()

        log.debug('/bpg.mutate')
        return self.mutations
