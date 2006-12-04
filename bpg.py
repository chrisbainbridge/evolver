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
BPG_MIN_UNROLLED_BODYPARTS = 2

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

def unroll_bodypart_copy(bp_o, skipNetwork):
    "return a copy of bp_o, without edges"
    # shallow copy first
    bp_c = copy.copy(bp_o)
    # now replace anything that we can't share or don't want
    if skipNetwork:
        bp_c.network = None
    else:
        bp_c.network = copy.deepcopy(bp_o.network)
    bp_c.edges = PersistentList()
    bp_c.input_map = None
    bp_c.motor_input = PersistentList([None,None,None])
    bp_c._v_instance_count = bp_o._v_instance_count
    assert bp_c._v_instance_count != None
    bp_c.genotype = bp_o
    return bp_c

def unroll_bodyparts(bp_o, bpg_c, bp_c, skipNetwork):
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
            child_bp_c = unroll_bodypart_copy(e.child, skipNetwork)
            e.child._v_instance_count += 1
            # add it to the copied bpg
            bpg_c.bodyparts.append(child_bp_c)
            # add it as a child to the copy bodypart. copy the edge.
            e_c = Edge(child_bp_c, e.joint_end, e.terminal_only)
            bp_c.edges.append(e_c)
            # recurse
            unroll_bodyparts(e.child, bpg_c, child_bp_c, skipNetwork)
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

def unroll_bodypart(bp_o, skipNetwork):
    "bp_o -- root BodyPart original."
    bpg_c = BodyPartGraph()
    if bp_o:
        # ignore rules.. we may as well always have a root bodypart if theres something there
        bp_c = unroll_bodypart_copy(bp_o, skipNetwork)
        bp_o._v_instance_count += 1
        assert bp_c
        bpg_c.root = bp_c
        bpg_c.bodyparts.append(bp_c)
        log.debug('unroll: added root bp')
        unroll_bodyparts(bp_o, bpg_c, bp_c, skipNetwork)
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
            self.randomInit(network_args)
        self.parentFitness = None
        self.numberOfMutations = None
        self.mutationStatRecorded = 0

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
        while 1:
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
            u = self.unroll(1)
            if len(u.bodyparts) >= BPG_MIN_UNROLLED_BODYPARTS:
                self.connectInputNodes()
                for bp in self.bodyparts:
                    for i in 0,1,2:
                        assert not bp.motor_input[i]
                self.sanityCheck()
                break

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
        # check that all motor inputs come from valid bodyparts
        for bp in p_bpg.bodyparts:
            for i in 0,1,2:
                if bp.motor_input[i]:
                    (b,s) = bp.motor_input[i]
                    assert b in p_bpg.bodyparts
        log.debug('p_bpg=%s (bodyparts=%s)'%(p_bpg, p_bpg.bodyparts))
        # find all unconnected nodes
        un = set([ (p_dst_bp, p_dst_signal) for p_dst_bp in p_bpg.bodyparts for p_dst_signal in p_dst_bp.network.inputs if not p_dst_signal.externalInputs ])
        # and unconnected motors
        un = un.union(set([ (p_dst_bp, 'MOTOR_%d'%i) for p_dst_bp in p_bpg.bodyparts for i in 0,1,2 if not p_dst_bp.motor_input[i] ]))

        for (p_dst_bp, p_dst_signal) in un:
            log.debug('UNCONNECTED bp %s signal %s', p_dst_bp, p_dst_signal)
            # find corresponding genotype of this node/motor
            g_bp = p_dst_bp.genotype
            if isinstance(p_dst_signal, node.Node):
                g_dst_signal = g_bp.network[p_dst_bp.network.index(p_dst_signal)]
                assert g_dst_signal in g_bp.network.inputs
            else:
                g_dst_signal = p_dst_signal
            # is there an entry in g_bp.input_map for the target node/motor? 
            if not g_bp.input_map.has_key(g_dst_signal):
                g_bp.input_map[g_dst_signal] = PersistentList()
            # are there matching maps for this phenotype topology?
            p_neighbours = p_bpg.getNeighbours(p_dst_bp)
            # find all neighbour bps with valid src bp,signal for this dst in input_map
            matches = [ (g_src_bp, g_src_signal, p_src_bp) for (g_src_bp, g_src_signal) in g_bp.input_map[g_dst_signal] for p_src_bp in p_neighbours if p_src_bp.genotype is g_src_bp]

            log.debug('input_map matches = %s', matches)
            p_source = None
            for (g_src_bp, g_src_signal, p_src_bp) in matches:
                log.debug('using prestored map g_src_bp=%s g_src_signal=%s', g_src_bp, g_src_signal)
                # convert genotype src signal to phenotype value
                if type(g_src_signal) is str:
                    p_source = (p_src_bp, g_src_signal)
                    break
                else:
                    # find phenotype src node
                    g_src_index = g_src_bp.network.index(g_src_signal)
                    p_src_node = p_src_bp.network[g_src_index]
                    if isinstance(p_dst_signal, node.Node) and isinstance(p_src_node, node.Node) and p_src_bp == p_dst_bp:
                        continue
                    # assert not two nodes in same bp network
                    assert not (isinstance(p_dst_signal, node.Node) and isinstance(p_src_node, node.Node)) or (p_src_bp != p_dst_bp)
                    # don't allow an external_input if the connection
                    # already exists internaly to the network
                    if not isinstance(p_dst_signal, node.Node) or p_src_node not in p_dst_signal.inputs:
                        # set source to a phenotype (bp,s)
                        p_source = (p_src_bp, p_src_node)
                        break
                    log.debug('rejected map - nodes already connected')

            if not p_source:
                # no entry in input_map for this node/motor
                # raise error if we aren't connecting up a genotype bpg
                assert backannotate
                # pick a random (bp, signal) from p_bp and backannotate into g_bp.input_map
                p_src_bp = random.choice(p_neighbours)
                # disallow connects from outnode to innode of same network
                posSrcs = ['CONTACT', 'JOINT_0', 'JOINT_1', 'JOINT_2']
                if type(p_dst_signal) == str or p_src_bp != p_dst_bp:
                    posSrcs += p_src_bp.network.outputs
                if isinstance(p_dst_signal, node.Node):
                    for x in posSrcs:
                        assert x not in p_dst_signal.inputs
                    # remove any possible srcs that node is already connected to
                    posSrcs = [x for x in posSrcs if x not in p_dst_signal.inputs]
                log.debug('possible connects %s <- %s', p_dst_signal, posSrcs)
                p_src_signal = random.choice(posSrcs)
                if isinstance(p_dst_signal, node.Node):
                    assert p_src_signal not in p_dst_signal.inputs
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

                log.debug('entering %s -> %s into bp.input_map', genosource, g_dst_signal)
                # add to genotype.input_map our backannotated source
                assert (g_dst_signal, genosource) not in g_bp.input_map.items()
                g_bp.input_map[g_dst_signal].append(genosource)
                assert g_bp in [ pbp.genotype for pbp in p_bpg.bodyparts ]

            # add to signal target.
            if isinstance(p_dst_signal, node.Node):
                p_dst_signal.addExternalInput(p_source)
            elif p_dst_signal[:6] == 'MOTOR_':
                i = ord(p_dst_signal[6])-ord('0')
                assert not p_dst_bp.motor_input[i]
                (sbp, ssig) = p_source
                log.debug('p_bp.motor_input[%d]=(%s,%s)'%(i,sbp,ssig))
                assert sbp in p_bpg.bodyparts
                p_dst_bp.motor_input[i] = p_source

        for bp in p_bpg.bodyparts:
            for i in 0,1,2:
                (b,s) = bp.motor_input[i]
                log.debug('p_bpg.bodyparts[%d].motor_input[%d]=(%s,%s)'%(p_bpg.bodyparts.index(bp),i,b,s))
                assert b in p_bpg.bodyparts

        log.debug('/connectInputNodes, calling sanityCheck')
        if sanitycheck:
            p_bpg.sanityCheck()

        log.debug('/BodyPartGraph.connectInputNodes')

    def getInputs(self, bp):
        """Return a list of all the external inputs to bodypart bp.
        
        Returns: [ (targetbp, (srcbp, signal)), ... ]"""

        if self.unrolled:
            sources = [ (neuron, externalInput) for neuron in bp.network.inputs for externalInput in neuron.externalInputs ]
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

    def unroll(self, skipNetwork=0):
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
        bpg = unroll_bodypart(self.root, skipNetwork)
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
                    assert n.externalInputs
                    for (sbp, src) in n.externalInputs:
                        assert sbp in phen_bpg.bodyparts
                        if isinstance(src, node.Node):
                            assert src in sbp.network.outputs
                            assert bp != sbp # no inter-network connections
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
