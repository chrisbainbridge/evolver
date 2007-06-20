import math
import os

from random import random, randint, uniform, choice
from copy import copy
from cPickle import loads, dumps
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from node import SigmoidNode, LogicalNode

import logging
log = logging.getLogger('neural')
log.setLevel(logging.INFO)

TOPOLOGIES = '1d', '2d', 'randomk', 'full'

class Network(PersistentList):
    "Model of a control network; nodes, edges, weights."

    def __init__(self, num_nodes, num_inputs, num_outputs, new_node_class,
            new_node_args, topology, update_style, radius=1):
        # what about k, quanta, nodes_per_input
        PersistentList.__init__(self)
        log.debug('Network.__init__()')
        self.outputs = PersistentList()
        self.domains = { 'bias' : (-5,5),
                         'state' : (0,1),
                         'weight' : (-7,7) }
        self.quanta = None
        # this is when we use a single update function (ca-like)
        self.function = None
        self.update_style = update_style
        # num_nodes must be bigger than inputs+outputs
        assert num_nodes >= num_inputs
        assert num_nodes >= num_outputs
        # create nodes
        inputsPerNode = self.getNumberOfInputsPerNode(topology, radius, num_nodes)
        if new_node_class == LogicalNode:
            new_node_args['numberOfInputs'] = inputsPerNode
        for _ in range(num_nodes):
            n = new_node_class(**dict(new_node_args))
            self.append(n)
        # select input nodes
        self.inputs = PersistentList()
        for _ in range(num_inputs):
            while 1:
                n = choice(self)
                if not n in self.inputs:
                    self.inputs.append(n)
                    break
        # select output nodes
        self.outputs = PersistentList()
        for _ in range(num_outputs):
            while 1:
                n = choice(self)
                if not n in self.outputs:
                    self.outputs.append(n)
                    break

        self.connect(topology, radius)
        for n in self:
            assert len(n.inputs) == inputsPerNode

    def __repr__(self):
        return 'Network[%d]'%len(self)

    def destroy(self):
        for n in self:
            n.destroy()

    def getNumberOfInputsPerNode(self, topology, neighbourhood_dist, num_nodes):
        if topology == '1d':
            return neighbourhood_dist * 2
        elif topology == '2d':
            neighbour_len = neighbourhood_dist*2+1
            return neighbour_len**2 - 1
        elif topology == 'randomk':
            return neighbourhood_dist
        else: #if topology == 'full':
            return num_nodes - 1

    def mutate(self, p):
        """Mutate the network with probability p of mutating each parameter.

        On average p*100 % of the network will be changed."""
        # MUTATE NODE POSITIONS IN TOPOLOGY
        # The topology never changes (except for ARBNS) so we just randomly
        # select two nodes and swap them
        self.mutations = 0
        self.check()
        for a_index in range(len(self)):
            # Since a change mutates two nodes, we halve p
            if random() < p/2:
                self.mutations += 1
                # choose another node to swap with
                b_index = a_index
                while b_index == a_index:
                    b_index = randint(0,len(self)-1)
                tmp_node = self[b_index]
                self[b_index] = self[a_index]
                self[a_index] = tmp_node
                # replace a with b and vice versa for all nodes inputs
                for n in self:
                    n.swapInputs(self[a_index], self[b_index])
                # swap input lists in a and b
                tmp_inputs = self[a_index].inputs
                self[a_index].inputs = self[b_index].inputs
                self[b_index].inputs = tmp_inputs
                # swap weights
                if hasattr(self[a_index], 'weights') \
                   and hasattr(self[b_index], 'weights'):
                    tmp_weights = self[a_index].weights
                    self[a_index].weights = self[b_index].weights
                    self[b_index].weights = tmp_weights
                # swap externalInputs
                t = self[a_index].externalInputs
                self[a_index].externalInputs = self[b_index].externalInputs
                self[b_index].externalInputs = t
                for i in a_index, b_index:
                    self[i].check()
                else:
                    for i in a_index, b_index:
                        self[i].fixup()

        # MUTATE NETWORK WIDE NODE UPDATE FUNCTION AND PARAMS, IF WE HAVE ONE
        if self.function:
            # mutate the function
            # with p probability we choose a random bit and replace it
            for x in range(len(self.function)):
                if random() < p:
                    self.mutations += 1
                    x = randint(0,len(self.function)-1)
                    self.function[x] = choice([0,1])

        # MUTATE INDIVIDUAL NODE AND PARAMS, OTHERWISE
        else:
            for node in self:
                m = node.mutate(p)
                self.mutations += m

        # mutate inputs and outputs
        for puts in self.inputs, self.outputs:
            for i in range(len(puts)):
                if random() < p:
                    self.mutations += 1
                    old = puts[i]
                    new = choice([x for x in self if x != old])
                    puts[i] = new
        return self.mutations

    def setState(self):
        for n in self:
            n.setState()

    def step(self):
        """Step every node in the network.

        Go through every neuron in the network sequentially and calculate
        its new state given current values from its incoming neurons.

        'input' neurons are ignored. Their state should be changed by
        external code.

        'sigmoid' neurons use the familiar weighted sum sigmoid
        calculation.

        Anything else is ignored and prints an error.

        """

        if self.update_style == 'sync':
            # synchronous - update all, then actually update the values
            for n in self:
                n.preUpdate()
            for n in self:
                n.postUpdate()
        elif self.update_style == 'async':
            # asynchronous - select randomly, then update, n times.
            for _ in range(len(self)):
                n = choice(self)
                n.preUpdate()
                n.postUpdate()
        else:
            assert 'bad update style %s'%self.update_style

    def check(self):
        log.debug('Network.check()')
        for x in self:
            x.check()

    def getNodeName(self, node_index):
        """Return a name for the node at node_index.

        Used for dot graphs etc.
        """
        # strip off network. at begining and Node at end
        name = str(type(self[node_index]))
        a = name.rfind('.')+1
        b = name.rfind("'")
        name = name[a:b]
        return name

    def connect(self, topology, neighbourhood_dist=1):
        log.debug('connect(%s)', topology)
        for n in self:
            assert not n.inputs
        if topology == '1d':
                self.connect1D(neighbourhood_dist)
        elif topology == '2d':
            self.connect2D(neighbourhood_dist)
        elif topology == 'randomk':
            self.connectRandomK(neighbourhood_dist)
        elif topology == 'full':
            self.connectFull()

    def connect1D(self, neighbourhood_dist):
        "1D ring, cells connect to every other cell in neighbourhood"
        log.debug('connect1D(%d)', neighbourhood_dist)
        # a 1D network with wrap around
        # go over all nodes calling target.addInput(src), with src
        # being the previous and next nodes in the network order
        neighbourhood = range(-neighbourhood_dist, 0) + range(1, neighbourhood_dist+1)
        for target_index in range(len(self)):
            # for the index of each node
            for src_offset in neighbourhood:
                log.debug('type of target node is %s',str(type(self[target_index])))
                #if not isinstance(self[target_index], InputNode):
                log.debug('Adding inputs to %s',str(self[target_index]))
                # for each offset connection to be made
                src_index = target_index+src_offset
                # map target_index to [0..len(self.network)-1]
                # ie. 1D wraparound
                src_index = src_index%len(self)
                log.debug('add link %s -> %s', str(self[src_index]), str(self[target_index]))
                self[target_index].addInput(self[src_index])

    def connect2D(self, neighbourhood_dist):
        """A 2D Moore neighbourhood (connect to all neighbours defined by a square boundary).

        FIXME: implement von neumann neighbourhood (cross boundary) as cmdline option.

        """
        log.debug('connect2D(num_nodes=%d, neighbourhood_dist=%d)', len(self), neighbourhood_dist)
        nodes_per_d = math.sqrt(len(self))
        if math.modf(nodes_per_d)[0]:
            raise '2d topology requested but number of nodes %d is not square'%len(self)

        neighbour_len = neighbourhood_dist*2+1
        # connect function doesn't work when neighbourhood length wraps around
        assert nodes_per_d >= neighbour_len
        # make a torus grid
        dimension_len = int(math.sqrt(len(self)))
        log.debug('Network2D.connect %dx%d network, neighbourhoods %dx%d',
                dimension_len, dimension_len, neighbour_len, neighbour_len)
        for i in range(dimension_len): # for dimension 1
            for j in range(dimension_len): # for dimension 2
                # for all nodes...
                target_index = i*dimension_len+j
                log.debug('target_index=%d', target_index)
                for y in range(i-neighbourhood_dist, i+neighbourhood_dist+1):
                    for x in range(j-neighbourhood_dist, j+neighbourhood_dist+1):
                        log.debug('src y,x=%d,%d', y, x)
                        # for coords over the neighbourhood rectangle but not target_node
                        wrapd_y = y%dimension_len
                        wrapd_x = x%dimension_len
                        src_index = wrapd_y*dimension_len+wrapd_x
                        if src_index != target_index:
                            log.debug('add link %s -> %s', str(self[src_index]), str(self[target_index]))
                            self[target_index].addInput(self[src_index])
        for n in self:
            assert len(n.inputs) == neighbour_len**2-1

    def connectRandomK(self, k):
        """Each node has a fixed number of inputs randomly chosen from other nodes.

        Since the topology is random it can be mutated, unlike most Networks."""
        log.debug('connectRandomK(%d)', k)
        for n in self:
            for _ in range(k):
                while 1:
                    r = choice(self)
                    if r != n: # and r not in n.inputs:
                        n.addInput(r)
                        break


    def connectFull(self):
        "Create connections joining every node to every other node"
        log.debug('connectFull()')
        for target in self:
            # make every other neuron a connected source neuron
            for source in self:
                 # not connecting to self and type is sigmoid node (what about others?)
                if target != source:
                    target.addInput(source)
