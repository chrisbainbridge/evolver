
## class Evaluation(Persistent):
##     """A neural network and its associated trial score

##     in_progress -- marks whether a client is currently evaluating this net"""

##     def __init__(self, solution=None, score=None):
##         """Create new evaluation.

##         Either has net or body, depending on what we are evaluating

##         solution -- a Network or a root BodyPart (when evolving whole creatures)
##         score -- score this solution got on its last trial
##         """
##         self.solution = solution
##         self.score = score
##         self.in_progress = 0

##     def __repr__(self):
##             return 'Evaluation(' + str(self.solution) + ',' + str(self.score)+ ')'

## class Generation(Persistent):
##     "Collection of Evaluations"

##     # representation for debug printing
##     def __repr__(self):
##         s = 'Generation('
##         for e in self._generation:
##             s += 'E(Net,' + str(e.score) + '),'
##         return s + ')'

##     def __init__(self):
##         self._generation = PersistentList()

##     def __getitem__(self, i):
##         return self._generation[i]

##     def __len__(self):
##         return len(self._generation)

##     def __getslice__(self,i,j):
##         return self._generation[i:j]

##     def add(self,net):
##        self._generation.append(net)

##     def sort(self):
##         self._generation.sort(lambda x,y: cmp(x.score, y.score))

##     def revsort(self):
##         self._generation.sort(lambda x,y: cmp(y.score, x.score))

## class Evolver(Persistent):
##     """Main evolution engine.

##     createInitialGeneration creates the first generation randomly, and
##     then evolve is called, which does the evaluations, storing the
##     results in a Generation which is added to the database.

##     self.generation is a list of Evals. An Eval is a wrapper for the
##     Morphology and/or Network and associated fitness trial scores."""

##     def __init__(self):
##         """Evolver init"""
##         self.sim = None
##         self.next_gen_lock = None
##         self.gen_num = 0
##         self.start_time = time.time()
##         self.random_state = random.getstate()
##         self.generation_sorted = 0
##         self.final_gen_num = 0

# just set .sim directly
#     def setSimulator(self, sim):
#         """Use the simulator for trials.

#         sim -- the class itself, not an instance."""
#         self.sim = sim

#    def setTrialTime(self, time):
#        self.eval_time = time



## class NetworkEvolver(Evolver):
##     """Evolve Network objects using some given Simulation as fitness test."""

##     def __init__(self, size, network_params):
##         """Create an initial generation

##         size -- number of solutions
##         network_params -- Everything about the Networks to create

##         Returns a Generation object."""

##         assert(size > 0)
##         log.info('Creating initial generation')
##         first_gen = PersistentList()
##         for i in range(size):
##             net = createNetwork(network_params)
##             first_gen.append(net)
##             # commit subtransaction
##             transaction.commit(1)
##             log.debug('created network #%d (type=%s, node_type=%s, ' +
##                   'num_nodes=%d, num_input=%d, num_output=%d, quanta=%s, domains(bias=%s, values=%s, ' +
##                   'weight=%s)', i, str(type(net)), str(type(net._network[0])),
##                   len(net._network), len(net.inputs), len(net.outputs), str(net.quanta),
##                   str(net.bias_domain), str(net.value_domain),
##                   str(net.weight_domain))
##         self.generation = first_gen

##     def createSim(self, net):
##         log.debug('evolve.createSim')
##         #assert isinstance(net, Network)
##         net.randomValue()
##         sim = eval(self.sim+'()')
##         sim.setSolution(net)
##         return sim
