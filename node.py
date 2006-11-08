import logging
import random
import math

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

log = logging.getLogger('node')
log.setLevel(logging.WARN)

# bin2int([1,1,1,0]) = 14
bin2int = lambda x: x and x[0]*2**(len(x)-1)+bin2int(x[1:]) or 0

class Node(Persistent):

    """A node has some input connections, an output, and a pointer
    back to the network."""

    def __init__(self):
        # self.inputs points to the source nodes for this node
        # if this node is an input, there should be a single source pointing to
        # (neighbour, output_node)
        # internal_inputs are from other nodes in the same network. we treat
        # them all the same
        self.inputs = PersistentList()
        # the external_input is from other networks, sensors etc. there should
        # be only one external input.
        # (note - this can also come from its own network, so its really a
        # non-topological input ie. external to the network topology)
        self.external_input = None

    def destroy(self):
        # delete references that can cause cycles
        del self.inputs
        del self.external_input

    def swapInputs(self, a, b):
        "If we have any inputs from a or b swap them over (for mutate)"
        log.debug('Node.swapInputs(%s,%s)', a, b)
        log.debug('self.inputs=%s', self.inputs)
        assert a != b

        for i in range(len(self.inputs)):
            if self.inputs[i] == a:
                self.inputs[i] = b
            elif self.inputs[i] == b:
                self.inputs[i] = a

    def addInput(self, source):
        log.debug('addInput(source=%s, inputs=%s)', source, self.inputs)
        # make sure we have no connections from this source
        assert source not in self.inputs
        self.inputs.append(source)

    def delInput(self, source):
        # make sure we have one and only one connection from this source
        assert source in self.inputs
        # remove from inputs
        self.inputs.remove(source)

    def check(self):
        pass

    def fixup(self):
        pass

def randomFromDomain((low,high), quanta=None):
    if quanta:
        #return random_quanta((low,high), quanta)
        return round(random.random()*quanta)/quanta*(high-low)+low
    else:
        return random.uniform(low, high)

def quantise(value, quanta):
    # quantise a value in domain [0,1]
    assert 0 <= value <= 1
    return round(quanta*value)/quanta

class SigmoidNode(Node):
    """A sigmoid neural node.

    The neurons are simple models (fixme: proper name?) that
    have internal bias (but no learning coefficient).

    Every neuron has a list of its incoming and output Connects which
    can be used to calculate new state and output values.

    state domain is always (0,1)
    """
    def __init__(self, bias_domain=(-5,5), weight_domain=(-7,7), quanta=None): #, network, discrete):
        #log.debug('creating SigmoidNode (network=%s, discrete=%s)', str(network), str(discrete))
        Node.__init__(self)
        #self.network = network
        #self.inputs = PersistentList()
        self.weights = PersistentMapping()
        self.bias_domain = bias_domain
        self.weight_domain = weight_domain
        self.quanta = quanta
        self.bias = randomFromDomain(self.bias_domain, quanta)
        self.randomiseState()

    def destroy(self):
        Node.destroy(self)
        del self.weights

    def randomiseState(self):
        self.state = randomFromDomain((0,1), self.quanta)

    def preUpdate(self):
        if not self.external_input:
            cumulative = 0
            for src in self.inputs:
                cumulative += src.state * self.weights[src]
                cumulative -= self.bias
            self.next_state = 1/(1+math.e**(-cumulative))
            if self.quanta:
                self.next_state = quantise(self.next_state, self.quanta)

    def postUpdate(self):
        if not self.external_input:
            self.state = self.next_state

    def mutate(self, p):
        # mutate the node bias
        mutations = 0
        if random.random() < p:
            mutations += 1
            self.bias = randomFromDomain(self.bias_domain, self.quanta)
        # mutate the incoming connection weights
        for src in self.weights.keys():
            if random.random() < p:
                mutations += 1
                self.weights[src] = randomFromDomain(self.weight_domain,
                                                     self.quanta)
        return mutations

    def addInput(self, source):
        Node.addInput(self, source)
        weight = randomFromDomain(self.weight_domain, self.quanta)
        self.weights[source] = weight

    def delInput(self, source):
        Node.delInput(self, source)
        del self.weights[source]

    def check(self):
        for key in self.weights.keys():
            assert key in self.inputs

    def fixup(self):
        # remove all weights that dont have an input
        for weight_key in self.weights.keys():
            if weight_key not in self.inputs:
                del(self.weights[weight_key])
        # add weight for any inputs that dont have one
        for source in self.inputs:
            if source not in self.weights:
                weight = self._chooseRandom()
                self.weights[source] = weight

    def swapInputs(self, a, b):
        Node.swapInputs(self, a, b)
        if a in self.weights and b in self.weights:
            t = self.weights[a]
            self.weights[a] = self.weights[b]
            self.weights[b] = t
        elif a in self.weights:
            self.weights[b] = self.weights[a]
            del self.weights[a]
        elif b in self.weights:
            self.weights[a] = self.weights[b]
            del self.weights[b]

    def getOutput(self):
        """The output attribute is a generic way to access the output value of
        any node. It should lie in the domain [0, 1]. If an output is set, use
        it, otherwise calculate one from the current state. In this case we can
        use the state directly since it should already be in 0..1"""
        return self.state

    def setOutput(self, value):
        if self.quanta:
            value = quantise(value, self.quanta)
        self.state = value

    output = property(getOutput, setOutput)

class MultiValueLogicFunction(PersistentList):
    """logical function of k inputs. outputs in the domain [low,high]
    
    Used by Logical node."""

    def __init__(self, numberOfInputs, numberOfStates):
        "Create a new random lookup table"
        PersistentList.__init__(self)
        self.numberOfStates = numberOfStates
        for _ in range(int(round(numberOfStates ** numberOfInputs))):
            self.append(self.getRandomValue())
        log.debug('MultiValueLogicFunction created %d entries', len(self))

    def getRandomValue(self):
        "Returns a random but valid value"
        randomValue = random.randint(0, self.numberOfStates-1)
        return randomValue

    def getValue(self, x):
        "Returns a stored value from the table"
        return self[x]
    
    def mutate(self, p):
        "Change a value in the table"
        # find a random row in the table, replace output with new randint
        m = 0
        for x in range(len(self)):
            if random.random() < p:
                self[x] = self.getRandomValue()
                m += 1
        return m

class LogicalNode(Node):
    """Output is a logical function of k inputs."""

    def __init__(self, numberOfInputs=None, numberOfStates=None, function=None):
        "Either use a previously generated function table, or make a new one"
        Node.__init__(self)
        if function:
            self.function = function
        else:
            assert numberOfInputs and numberOfStates
            self.function = MultiValueLogicFunction(numberOfInputs, numberOfStates)

    def preUpdate(self):
        "Convert inputs to a decimal value and lookup in logic function"
        x = 0
        for i in range(len(self.inputs)):
            x += i * self.function.numberOfStates * self.inputs[i].state
        assert isinstance(x, int)
        self.state_next = self.function.getValue(x)

    def postUpdate(self):
        self.state = self.state_next

    def randomiseState(self):
        self.state = self.function.getRandomValue()

    def mutate(self, p):
        "Mutate the function"
        m = self.function.mutate(p)
        return m

    def getOutput(self):
        x = self.state / (self.function.numberOfStates-1)
        return x

    def setOutput(self, x):
        self.state = int(round(x * (self.function.numberOfStates-1)))
        assert isinstance(self.state, int)
    
    output = property(getOutput, setOutput)
