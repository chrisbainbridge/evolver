import logging
import random
import math
from rand import rnd

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

log = logging.getLogger('node')
log.setLevel(logging.WARN)

def randomFromDomain((low,high), v, quanta=None):
    if quanta and v != None:
        x = round(rnd(0,quanta-1,(v-low)/(high-low)*(quanta-1.0)))
        return x/(quanta-1.0)*(high-low)+low
    else:
        return rnd(low, high, v)

def quantise(value, quanta):
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
        if isinstance(s_sig, Node):
            assert s_sig in s_bp.network
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

    def wsum(self, inputs=None, use_external=1):
        'sum of weighted inputs'
        cumulative = 0
        if inputs==None:
            inputs = self.inputs
        for src in inputs:
            cumulative += src.output * self.weights[src]
        if use_external:
            for (src, value) in self.externalInputs.items():
                cumulative += value * self.weights[src]
        return cumulative

class SigmoidNode(WeightNode):
    'Sigmoid model (no internal state)'

    def __init__(self, weightDomain=(-7,7), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.reset()

    def postUpdate(self):
        'return output in [0,1]'
        self.output = 1/(1 + math.e**-self.wsum())

    def reset(self):
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
        self.reset()
        self.setAmplitude()
        self.postUpdate()

    def setPhaseOffset(self):
        self.phaseOffset = rnd(0, 2*math.pi, self.phaseOffset)

    def setStepSize(self):
        # oscillate between [twice per second, once every 2 seconds)
        persec = math.pi*2/50
        self.stepSize = rnd(persec/2, persec*2, self.stepSize)

    def reset(self):
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

    def __init__(self, weightDomain=(-16,16), quanta=None, biasDomain=(-4,4)):
        WeightNode.__init__(self, weightDomain, quanta)
        self.adaptRate = None
        self.bias = None
        self.state = None
        self.setAdaptRate()
        self.biasDomain = biasDomain
        self.setBias()
        self.reset()

    def preUpdate(self):
        DT = 1.0 / 50
        self.nextState = self.state + DT * (self.wsum() - self.state) / self.adaptRate

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
        # suggested value is 1
        self.adaptRate = rnd(0.5, 5, self.adaptRate)

    def setBias(self):
        # suggested value is 2
        self.bias = randomFromDomain(self.biasDomain, self.bias, self.quanta)

    def reset(self):
        self.state = rnd(-0.1, 0.1, self.state) # should internal state be quantised?
        self.output = 1/(1 + math.e**-(self.state + self.bias))

class TagaNode(WeightNode):
    'Taga 2nd order model'

    def __init__(self, weightDomain=(-4,4), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.tau0 = 1.0
        self.tau1 = 1.0
        self.beta = 2.5
        self.b = 1.0
        self.reset()

    def reset(self):
        self.u = 0
        self.v = 0
        self.setOutput()

    def setOutput(self):
        self.output = max(0, self.u)

    def preUpdate(self):
        DT = 1.0 / 50
        self.next_u = self.u + DT * (-self.u - self.beta*max(0,self.v) + self.wsum() + self.b) / self.tau0
        self.next_v = self.v + DT * (-self.v + self.output) / self.tau1

    def postUpdate(self):
        self.u = self.next_u
        self.v = self.next_v
        self.setOutput()

class WallenNode(WeightNode):
    'Wallen 3rd order model'

    def __init__(self, weightDomain=(0,16), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        assert weightDomain[0] == 0

        self.theta = [-0.2, 0.1, 0.5, 8.0]
        self.r = [1.8, 0.3, 1.0, 0.5]
        self.tau_d = [0.03, 0.02, 0.02, 0.05]
        self.mu = [0.3, 0.0, 0.3, 0.0]
        self.tau_a = [0.400, 0.001, 0.2, 0.001] # rm 0s: / by 0 in 3rd eq.

        self.setI()
        self.excite = random.choice([True,False])
        self.ye = None
        self.yi = None
        self.yt = None
        self.reset()

    def setI(self):
        'i selects the neuron type from the predefined values'
        self.i = random.randint(0,3)

    def reset(self):
        self.yt = rnd(-0.1, 0.1, self.yt)
        self.ye = rnd(-0.1, 0.1, self.ye)
        self.yi = rnd(-0.1, 0.1, self.yi)
        self.setOutput()

    def setOutput(self):
        self.output = max(0, 1 - math.e**(self.r[self.i]*(self.theta[self.i] - self.ye)) - self.yi - self.mu[self.i]*self.yt)

    def preUpdate(self):
        excite_inputs = [x for x in self.inputs if x.excite]
        inhibit_inputs = [x for x in self.inputs if not x.excite]
        # here we are assuming that all sensory input is excitatory
        DT = 1.0 / 50
        self.next_ye = self.ye + DT * (-self.ye + self.wsum(excite_inputs)) / self.tau_d[self.i]
        self.next_yi = self.yi + DT * (-self.yi + self.wsum(inhibit_inputs, 0)) / self.tau_d[self.i]
        self.next_yt = self.yt + DT * (-self.yt + self.output)/self.tau_a[self.i]

    def postUpdate(self):
        self.ye = self.next_ye
        self.yi = self.next_yi
        self.yt = self.next_yt
        self.setOutput()

    def mutate(self, p):
        mutations = 0
        mutations += WeightNode.mutate(self, p)
        if random.random() < p:
            self.setI()
            mutations += 1
        if random.random() < p:
            self.excite = not self.excite
            mutations += 1
        return mutations

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

    def reset(self):
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
