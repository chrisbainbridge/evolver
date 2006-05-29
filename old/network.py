

#        if num_inputs:
#            self.createInputNodes(num_inputs, node_type, nodes_per_input)
        # choose outputs
#        if num_outputs:
#            self.createOutputNodes(num_outputs, node_type, nodes_per_input)

##     def createInputNodes(self, num_inputs, node_type, nodes_per_input):
##         """Create all the input nodes.

##         num_inputs -- number of nodes to create
##         node_type -- type 'sigmoid' or 'logical'
##         nodes_per_input -- number of nodes to map input onto

##           eg. we can map a [0..1] input onto 8 boolean nodes with 256
##           possible values, by creating a single MultiNodeLogicalInput
##           connected to the actual LogicalInputNodes in the Network.

##         The InputNodes are randomly placed over regular non-IO nodes
##         in the Network. This ensures that the topology and total
##         number of nodes remain constant.

##         """

##         log.debug('Network.createInputNodes(%d,%s,%d)'%(num_inputs, node_type, nodes_per_input))
##         # for all inputs, create, randomly place over existing node_type
##         # (we are not connected yet, so dont worry about that
##         for _ in range(num_inputs):
##             # if we only have one node_per_input, map it directly onto an InputNode
##             if nodes_per_input == 1:
##                 if node_type == 'sigmoid':
##                     n = ScalarInputNode(self, self.quanta)
##                 elif node_type == 'logical':
##                     n = LogicalInputNode(self)
##                 else:
##                     log.debug('node_type %s not recognised', node_type)
##                 self.inputs.append(n)
##                 #self.append(n)
##                 self.randomOverwrite(n)
##             # else create a list of several InputNodes
##             else:
##                 # this is the only multinode defined so far
##                 n = MultiNodeLogicalInputNode(self, nodes_per_input)
##                 #self += n.nodeset
##                 self.randomOverwrite(n.nodeset)
##                 self.inputs.append(n)
##                 # _network has all the individual nodes, but inputs has the MultiNodeXX...

##     def createOutputNodes(self, num_outputs, node_type, nodes_per_output):
##         """create all the output nodes"""

##         assert len(self.outputs) == 0
##         log.debug('Network.createOutputNodes(%d,%s,%d)'%(num_outputs, node_type, nodes_per_output))
##         if num_outputs > len(self):
##             num_outputs = len(self)
##         for _ in range(num_outputs):
##             # fixme: should be exclusive outputs
##             t = []
##             for n in self:
##                 if self.outputs.count(n) == 0:
##                     t.append(n)
##             self.outputs.append(choice(t))
## ##             # if we only have one node_per_input, map it directly onto an InputNode
## ##             if nodes_per_output == 1:

## ## ##                 if node_type == 'sigmoid':
## ## ##                     n = SigmoidOutputNode(self, self.quanta)
## ## ##                 elif node_type == 'logical':
## ## ##                     n = LogicalOutputNode(self)
## ## ##                 else:
## ## ##                     log.debug('node_type %s not recognised', node_type)
## ## ##                 self.outputs.append(n)
## ## ##                 self.randomInsert(n)
## ##                 self.outputs.append(random.choice(self)
## ##             # else create a list of several OutputNodes
## ##             else:
## ##                 # a multiple output node will have a getOutput method
## ##                 # and know about several other nodes, but will not
## ##                 # actually be part of the network
## ##                 n = MultiNodeLogicalOutputNode(self, nodes_per_output)
## ##                 #self += n.nodeset
## ##                 self.randomInsert(n)
## ##                 self.inputs.append(n)
## ##                 # _network has all the individual nodes, but inputs has the MultiNodeXX...



##     def connectLogical(self):
##         for n in self:
##             if type(n) is LogicalNode:
##                 n.randomConnect(self)

##     def randomCAFunction(self):
##         # make a random self.function here to be used by the CANodes
##         # k is the number of neighbours
##         self.function = PersistentList()
##         for _ in range(2**len(self.ca_neighbourhood)):
##             self.function.append(choice([0,1]))

##     def randomBoolFunction(self):
##         for n in self:
##             if type(n) is BooleanNode:
##                 n.randomFunction()

##     def setBiasDomain(self, domain):
##         """Restrict values used for internal neuron bias to be between low and high.

##         This only affects neural nodes which support internal bias.
##         """
##         self.bias_domain = domain

##     def setValueDomain(self, domain):
##         """Restrict values output by each node to be between low and high.

##         This is not useful for nodes that just output a mapping eg. boolean nodes
##         """
##         self.value_domain = domain

##     def setWeightDomain(self, domain):
##         """Restrict weight values on connections to be between low and high."""
##         self.weight_domain = domain

##     def useDiscreteQuanta(self, quanta):
##         """Use discrete quanta for the Node states and other values.

##         quanta -- how many quanta to use for discrete values

##         This only works with Sigmoid nodes. The default is to use
##         continuous values. Logical nodes use states but lookup tables
##         instead of the Sigmoid transfer function, and so will be
##         unaffected by this method.

##         Connection weights, neuron state, internal bias, learning bias
##         (if present), and output values are all quantised.  """
##         self.quanta = quanta




#    def randomOverwrite(self, node):
#        """Insert node into a random position of the network.

#        Doesn't overwrite InputNodes or OutputNodes.
#        node can be a list of nodes.
#        """
#        if isinstance(node, Node):
#            todo = [node]
#        elif isinstance(node, list):
#            todo = node
#        else:
#            raise 'whats that %s?'%(type(node))

#        num_free = 0
#        log.debug('len(network) = %d', len(self))
#        for n in self:
#            #if not isinstance(n, InputNode) and not isinstance(n, OutputNode):
#            if not n not in self.inputs and n not in self.outputs:
#                num_free += 1
#        log.debug('num_free = %d', num_free)

#        assert num_free >= len(todo)

#        for n in todo:
#            inserted = 0
#            while not inserted:
#                # choose random overwrite point
#                x = randint(0, len(self)-1)
#                #and not isinstance(self[x], OutputNode):
#                if not self[x] in self.inputs and self[x] not in self.outputs: 
#                    # overwrite
#                    # FIXME: preserve topology?
#                    self[x] = n
#                    inserted = 1



##     def numberOfNodes(self):
##         """Return the total number of nodes in the network."""
##         return len(self)

##     def enableTrace(self):
##         # declare all signals
##         # name all nodes
##         self.trace = 1
##         self.node_names = [] #PersistentList() # doesnt need to be persistent
##         for i in range(len(self)):
##             name = self.getNodeName(i)
##             self.node_names.append(name)
##             trace.declareSignal(name)



##     def __str__(self):
##         # print representation for debugging
##         return 'Network()'

##     def updateInputs(self, inputlist):

##         """Since the caller doesn't know what the inputs are going to
##         be mapped onto we need some common signal. Define each input
##         as being continuous and between 0 and 1. It is up to the
##         caller to ensure that this is the case.

##         How are input values mapped to InputNodes? It's assumed that
##         inputlist is in the correct order to map directly onto
##         self.inputs (the list of InputNodes created when the network
##         is created).

##         """

##         # make sure we have enough input values, but not too many!
##         assert(len(inputlist) == len(self.inputs))
##         # sanity check all inputs
##         for x in inputlist:
##             assert(x>=0 and x<=1)
##         # calls updateInput for each input object
##         # (Might be a multinode object)
##         for i in range(len(self.inputs)):
##             self.inputs[i].updateInput(inputlist[i])

##     def traceNodes(self):
##         """Write internal state of all neurons to the trace file now."""
##         if self.trace:
##             for i in range(len(self)):
##                 if hasattr(self[i], '_v_value'):
##                     trace.logValue(self.node_names[i], self[i]._v_value)
## #            else:
## #                log.debug('missing _v_value in %s, substituting 0 ',str(type(n)))
## #                self.trace_file.write(' '+str(0))



##     def getOutputValues(self):
##         """Get all OutputNode values."""
##         output_values = []
##         for n in self.outputs:
##             x = n.getOutput()
##             output_values.append(x)

##         return output_values



##     def mutate(self, p):
##         # MUTATE THE TOPOLOGY
##         if random() < p:
##             # select a random input to change
##             x = randint(0,len(self.inputs)-1)
##             # make it point from some random node in the network
##             self.inputs[x] = choice(self)
##         # mutate everything else
##         Network.mutate(self, p)
