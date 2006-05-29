import math
import os

from random import random, randint, uniform, choice
from copy import copy
from cPickle import loads, dumps
from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from node import *

import logging
log = logging.getLogger('neural')
log.setLevel(logging.INFO)

class Network(PersistentList):
    "Model of a control network; nodes, edges, weights."
    def __init__(self, num_nodes, num_inputs, num_outputs, new_node_fn,
            new_node_args, topology, update_style, nb_dist=1):
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
        for _ in range(num_nodes):
            n = new_node_fn(**dict(new_node_args))
            self.append(n)
        # select input nodes
        self.inputs = PersistentList()
        for _ in range(num_inputs):
            while 1:
                n = random.choice(self)
                if not n in self.inputs:
                    self.inputs.append(n)
                    break
        # select output nodes
        self.outputs = PersistentList()
        for _ in range(num_outputs):
            while 1:
                n = random.choice(self)
                if not n in self.outputs:
                    self.outputs.append(n)
                    break

        if topology:
            self.connect(topology, nb_dist)

    def mutate(self, p):
        """Mutate the network with probability p of mutating each parameter.

        On average p*100 % of the network will be changed."""
        # MUTATE NODE POSITIONS IN TOPOLOGY
        # The topology never changes (except for ARBNS) so we just randomly
        # select two nodes and swap them
        mutations = 0
        for a_index in range(len(self)):
            # Since a change mutates two nodes, we halve p
            if random.random() < p/2:
                mutations += 1
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
                    mutations += 1
                    x = randint(0,len(self.function)-1)
                    self.function[x] = choice([0,1])
 
        # MUTATE INDIVIDUAL NOD AND PARAMS, OTHERWISE
        else:
            for node in self:
                m = node.mutate(p)
                mutations += m

        # mutate inputs and outputs
        for puts in self.inputs, self.outputs:
            for i in range(len(puts)):
                if random.random() < p:
                    mutations += 1
                    old = puts[i]
                    new = random.choice([x for x in self if x != old])
                    puts[i] = new
                    # fixup
                    #if puts is self.inputs and old not in self.inputs:
                    #    old.external_input = None
                    # but other things point to this thinking its an output
        return mutations

    def randomiseState(self):
        for n in self:
            n.randomiseState()

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

    def plotNodes(self, toponly=0, prefix='n'):
        s = ''
        # write out all nodes
        for i in range(len(self)):
            if toponly:
                s += '  %s%d [shape=point]\n'%(prefix, i)
            else:
                name = self.getNodeName(i)
                label = '%d'%i
                if self[i] in self.inputs:
                    label += 'i'
                if self[i] in self.outputs:
                    label += 'o'
                label += '-'+name
                s += '  %s%d [label="%s"]\n'%(prefix, i, label)
        return s

    def plotEdges(self, toponly=0, prefix='n'):
        s = ''
        done = {}
        # write out all edges
        for target_index in range(len(self)):
            n = self[target_index]
            if n in self.inputs:
                continue
            for i in n.inputs:
                src_index = self.index(i)
                if not toponly or not done.has_key((target_index,src_index)):
                    edge_label = ''
                    if not toponly and hasattr(self[target_index],'weights'):
                        try:
                            w = self[target_index].weights[self[src_index]]
                            sl = str(w)
                            sl = sl[:sl.find('.')+2]
                            edge_label = sl
                        except KeyError:
                            pass
                    if edge_label:
                        s += '  %s%d -> %s%d [label="%s"]\n'%(prefix, src_index, prefix, target_index, edge_label)
                    elif toponly:
                        s += '  %s%d -> %s%d [dir=none]\n'%(prefix, src_index, prefix, target_index) # or dir=both
                    else:
                        s += '  %s%d -> %s%d\n'%(prefix, src_index, prefix, target_index)
                    done[(src_index, target_index)] = 1
        return s
        
    def plot(self, filename=None, toponly=0):
        """Dump this network as a (graphviz) dot file."""
        log.debug('dumping network to %s in dot graph format', filename)
        s = 'digraph G {\n'
        s += self.plotNodes(toponly)
        s += self.plotEdges(toponly)
        s += '}'
        if filename:
            (fbase, ext) = os.path.splitext(filename)
            ext = ext[1:]
            f = open(fbase+'.dot', 'w')
            f.write(s)
            f.close()
            if ext != 'dot':
                os.system('dot -T%s -o%s.%s %s.dot'%(ext, fbase, ext, fbase))
                os.remove(fbase+'.dot')
        return s

    def connect(self, topology, neighbourhood_dist=1):
        log.debug('connect(%s)', topology)
        if topology == '1d':
                self.connect1D(neighbourhood_dist)
        elif topology == '2d':
            self.connect2D(neighbourhood_dist)
        elif topology == 'randomk':
            self.connectRandomK()
        elif topology == 'full':
            self.connectFull()
        else:
            fail

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
        if nodes_per_d%1.0 != 0:
            raise '2d topology requested but number of nodes %d is not square'%len(self)

        neighbour_len = neighbourhood_dist*2+1
        # connect function doesn't work when neighbourhood length wraps around 
        assert nodes_per_d >= neighbour_len
        # make a torus grid
        #assert neighbourhood_dist%2 == 1 # must be odd
        #max_d = (neighbour_len-1)/2
        dimension_len = int(math.sqrt(len(self))) #int(math.pow(len(self), 1.0/2))
        log.debug('Network2D.connect %dx%d network, neighbourhoods %dx%d',
                dimension_len, dimension_len, neighbour_len, neighbour_len)
#        log.debug('creating neighbourhoods with dimensions %dx%d',
#        neighbour_len, neighbour_len)
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

    def connectRandomK(self, listofnodes):
        """Each node has a fixed number of inputs randomly chosen from other nodes.

        Since the topology is random it can be mutated, unlike most Networks."""
        log.debug('connectRandomK(%d)', k)
        fixme - arg is distance, not listofnodes
        # initialise self.inputs
        for _ in range(self.k):
            self.inputs.append(choice(listofnodes))

    def connectFull(self):
        "Create connections joining every node to every other node"
        log.debug('connectFull()')
        for target in self:
            # make every other neuron a connected source neuron
            for source in self:
                 # not connecting to self and type is sigmoid node (what about others?!)
                if target != source:
                    target.addInput(source)
