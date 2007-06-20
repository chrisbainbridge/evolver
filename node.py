import logging
import random
import math
from rand import rnd

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

log = logging.getLogger('node')
log.setLevel(logging.WARN)

# bin2int([1,1,1,0]) = 14
bin2int = lambda x: x and x[0]*2**(len(x)-1)+bin2int(x[1:]) or 0

def randomFromDomain((low,high), v, quanta=None):
    if quanta and v != None:
        x = round(rnd(0,quanta-1,(v-low)/(high-low)*(quanta-1.0)))
        return x/(quanta-1.0)*(high-low)+low
#        return random.randint(0,quanta-1)/(quanta-1.0)*(high-low)+low
    else:
        return rnd(low, high, v)

def quantise(value, quanta):
    # quantise a value in domain [0,1]
    assert 0 <= value <= 1
    return round(quanta*value)/quanta

class Node(Persistent):

    def __init__(self):
        self.inputs = PersistentList() # list of internal inputs
        # externalInputs[(bp,sig)] = signalvalue
        self.externalInputs = PersistentMapping()

    def destroy(self):
        # delete references that can cause cycles
        del self.inputs
        del self.externalInputs

    def check(self):
        pass

    def fixup(self):
        pass

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

    def addExternalInput(self, source):
        log.debug('addExternalInput(source=%s, externalInputs=%s)', source, self.externalInputs)
        # make sure we have no connections from this source
        assert source not in self.externalInputs
        self.externalInputs[source] = 0 # default initial value

    def removeExternalInput(self, bp, sig):
        log.debug('removeExternalInput(source=%s, externalInputs=%s)', (bp,sig), self.externalInputs)
        del self.externalInputs[(bp,sig)]

    def preUpdate(self):
        pass

class WeightNode(Node):
    'A traditional model neuron: state in [0,1], weighted inputs'

    def __init__(self, weightDomain=(-7,7), quanta=None):
        Node.__init__(self)
        self.weights = PersistentMapping()
        self.weightDomain = weightDomain
        self.quanta = quanta
        self.output = random.uniform(0,1)

    def destroy(self):
        Node.destroy(self)
        del self.weights

#    def setState(self):
#         this is not really state, it's just the initial output
#         but it is the only bit of state the simulator can randomise
#        self.output = random.uniform(0,1)

    def randomWeight(self):
        return randomFromDomain(self.weightDomain, self.quanta)

    def mutate(self, p):
        mutations = 0
        for src in self.weights.keys():
            if random.random() < p:
                mutations += 1
                self.weights[src] = self.randomWeight()
        return mutations

    def addInput(self, source):
        Node.addInput(self, source)
        self.weights[source] = self.randomWeight()

    def addExternalInput(self, s_bp, s_sig, weight):
        'source = (srcBodypart, srcSignal, weight)'
        source = (s_bp, s_sig)
        Node.addExternalInput(self, source)
        self.weights[source] = weight

    def removeExternalInput(self, bp, sig):
        'source = (srcBodypart, srcSignal)'
        Node.removeExternalInput(self, bp, sig)
        del self.weights[(bp,sig)]

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

    def sumOfWeightedInputs(self):
        cumulative = 0
        for src in self.inputs:
            cumulative += src.output * self.weights[src]
        for (src, value) in self.externalInputs.items():
            cumulative += value * self.weights[src]
        return cumulative

#    def getOutput(self):
#        return self._output

#    def setOutput(self, v):
#        self._output = v
#        if self.quanta:
#            self._output = quantise(self._output, self.quanta)
#    output = property(getOutput, setOutput)

class SigmoidNode(WeightNode):
    'Sigmoid model (no internal state)'

    def __init__(self, weightDomain=(-7,7), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.setState()

    def postUpdate(self):
        'return output in [0,1]'
        self.output = 1/(1 + math.e**-self.sumOfWeightedInputs())

    def setState(self):
#         this is not really state, it's just the initial output
#         but it is the only bit of state the simulator can randomise
        self.output = rnd(0,1,self.output)

class SineNode(WeightNode):
    'Sine wave model'

    def __init__(self, weightDomain=(-7,7), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.phaseOffset = None
        self.stepSize = None
        self.amplitude = None
        self.setPhaseOffset()
        self.setStepSize()
        self.setState()
        self.setAmplitude()
        self.postUpdate()

    def setPhaseOffset(self):
        self.phaseOffset = rnd(0, 2*math.pi, self.phaseOffset)

    def setStepSize(self):
        # oscillate between [twice per second, once every 2 seconds)
        persec = math.pi*2/50
        self.stepSize = rnd(persec/2, persec*2, self.stepSize)

    def setState(self):
        self.state = self.phaseOffset

    def setAmplitude(self):
        self.amplitude = rnd(0.25, 1, self.amplitude)

    def postUpdate(self):
        'return output in [0,1]'
        self.output = (math.sin(self.state)*self.amplitude + 1) / 2
        self.state = (self.state + self.stepSize) % (2*math.pi)

    def mutate(self, p):
        mutations = 0
        if random.random() < p:
            self.setStepSize()
            mutations += 1
        if random.random() < p:
            self.setPhaseOffset()
            mutations += 1
        if random.random() < p:
            self.setAmplitude()
            mutations += 1
        return mutations

class BeerNode(WeightNode):
    'Beer 1st order model'

    def __init__(self, weightDomain=(-16,16), quanta=None, biasDomain=(-16,16)):
        WeightNode.__init__(self, weightDomain, quanta)
        self.adaptRate = None
        self.bias = None
        self.state = None
        self.setAdaptRate()
        self.biasDomain = biasDomain
        self.setBias()
        self.setState()

    def preUpdate(self):
        self.nextState = self.state + 0.1 * ((self.sumOfWeightedInputs() - self.state) / self.adaptRate)

    def postUpdate(self):
        self.state = self.nextState
        self.output = 1/(1 + math.e**-(self.state + self.bias))

    def mutate(self, p):
        mutations = 0
        mutations += WeightNode.mutate(self, p)
        if random.random() < p:
            self.setAdaptRate()
            mutations += 1
        if random.random() < p:
            self.setBias()
            mutations += 1
        return mutations

    def setAdaptRate(self):
        self.adaptRate = rnd(0.5, 10, self.adaptRate)

    def setBias(self):
        self.bias = randomFromDomain(self.biasDomain, self.bias, self.quanta)

    def setState(self):
        self.state = rnd(-0.1, 0.1, self.state) # should internal state be quantised?
        self.output = 1/(1 + math.e**-(self.state + self.bias))

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

    def setState(self):
        self.state = self.function.getRandomValue()
        self.postUpdate()

    def preUpdate(self):
        "Convert inputs to a decimal value and lookup in logic function"
        x = 0
        for i in range(len(self.inputs)):
            x += i * self.function.numberOfStates * self.inputs[i].state
        assert isinstance(x, int)
        self.nextState = self.function.getValue(x)

    def postUpdate(self):
        self.output = self.state / (self.function.numberOfStates-1)

    def mutate(self, p):
        "Mutate the function"
        m = self.function.mutate(p)
        return m
