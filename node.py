import logging
import random
import math
from rand import rnd

from persistent import Persistent
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping

log = logging.getLogger('node')
log.setLevel(logging.WARN)

def rdom((low,high), v=None, quanta=None):
    """random value from domain where existing value=v if rand.usegauss is set,
    or uniform otherwise. If quanta is set, quantise the returned value."""
    if quanta and v != None:
        x = round(rnd(0,quanta-1,(v-low)/(high-low)*(quanta-1)))
        return x/(quanta-1.0)*(high-low)+low
    else:
        x = rnd(low, high, v)
        if quanta:
            x = round((x-low)/(high-low)*(quanta-1))*(high-low)/(quanta-1)+low
    return x

def quantise(value, quanta):
    "quantise value between 0 and 1. Used for neuron outputs."
    assert 0 <= value <= 1
    if not quanta:
        return value
    return round((quanta-1)*value)/(quanta-1)

def quantiseDomain((l,h), x, q):
    # in order to quantise we need to cap the domain
    x = min(max(x,l),h)
    if not q:
        return x
    return round((float(x)-l)/(h-l)*(q-1))*(h-l)/(q-1)+l

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

    def __init__(self, weightDomain=(-7,7), quanta=None, abs_weights=0):
        # with absolute weights and polarity neurons range must be >= 0.
        if abs_weights:
            assert weightDomain[0] >= 0
        Node.__init__(self)
        self.weights = PersistentMapping()
        self.weightDomain = weightDomain
        self.quanta = quanta
        self.output = random.uniform(0,1)
        # abs_weights only affects external inputs since weightDomain is forced
        # to be positive above
        self.abs_weights = abs_weights

    def destroy(self):
        Node.destroy(self)
        del self.weights

    def mutate(self, p):
        mutations = 0
        for src in self.weights.keys():
            if random.random() < p:
                mutations += 1
                self.weights[src] = rdom(self.weightDomain, self.weights[src], self.quanta)
        return mutations

    def addInput(self, source):
        Node.addInput(self, source)
        self.weights[source] = rdom(self.weightDomain, None, self.quanta)

    def addExternalInput(self, s_bp, s_sig, weight):
        'source = (srcBodypart, srcSignal, weight)'
        source = (s_bp, s_sig)
        if isinstance(s_sig, Node):
            assert s_sig in s_bp.network
        Node.addExternalInput(self, source)
        if self.abs_weights:
            weight = abs(weight)
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
        # quantise inputs
        for src in inputs:
            x = src.output
            if self.quanta:
                x = quantise(x, self.quanta)
            cumulative += x * self.weights[src]
        if use_external:
            for (src, x) in self.externalInputs.items():
                if self.quanta:
                    x = quantise(x, self.quanta)
                cumulative += x * self.weights[src]
        return cumulative

class SigmoidNode(WeightNode):
    'Sigmoid model (no internal state)'

    def __init__(self, weightDomain=(-7,7), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.reset()

    def postUpdate(self):
        'return output in [0,1]'
        self.output = 1/(1 + math.e**-self.wsum())
        # quantise output
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

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
        self.phaseOffset = rdom((0,2*math.pi), self.phaseOffset, self.quanta)

    def setStepSize(self):
        # oscillate between [twice per second, once every 2 seconds)
        persec = math.pi*2/50
        self.stepSize = rdom((persec/2, persec*2), self.stepSize, self.quanta)

    def reset(self):
        self.state = self.phaseOffset

    def setAmplitude(self):
        self.amplitude = rdom((0.25, 1), self.amplitude, self.quanta)

    def postUpdate(self):
        'return output in [0,1]'
        self.output = quantise((math.sin(self.state)*self.amplitude + 1) / 2, self.quanta)
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
        # cap state to [-4,4]. This isn't part of the normal model but we need
        # clear boundaries for quantisation. +-4 is enough to define a clear
        # output range that almost gets to 0 and 1.
        self.nextState = quantiseDomain((-4,4), self.nextState, self.quanta)

    def postUpdate(self):
        self.state = self.nextState
        self.output = 1/(1 + math.e**-(self.state + self.bias))
        # quantise output
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

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
        # suggested value is 1, but this is very low when combined with Euler
        # step size of 1/50.
        self.adaptRate = rdom((0.05,0.5), self.adaptRate, self.quanta)

    def setBias(self):
        # suggested value is 2
        self.bias = rdom(self.biasDomain, self.bias, self.quanta)

    def reset(self):
        self.state = rdom((-0.1,0.1), self.state, self.quanta)
        self.output = 1/(1 + math.e**-(self.state + self.bias))
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

class TagaNode(WeightNode):
    'Taga 2nd order model'

    def __init__(self, weightDomain=(-4,4), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta)
        self.tau0 = 0.2 # originally 1.0, but very slow, this seems to work better.
        self.tau1 = 0.2 # also 1.0
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

        self.next_u = quantiseDomain((-1,1), self.next_u, self.quanta)
        self.next_v = quantiseDomain((0,1), self.next_v, self.quanta)

    def postUpdate(self):
        self.u = self.next_u
        self.v = self.next_v
        self.setOutput()

class WallenNode(WeightNode):
    'Wallen 3rd order model'

    def __init__(self, weightDomain=(0,16), quanta=None):
        WeightNode.__init__(self, weightDomain, quanta, 1)
               # i =    0      1      2     3
        self.theta = [-0.2,   0.1,   0.5,  8.0  ]
        self.r     = [ 1.8,   0.3,   1.0,  0.5  ]
        self.tau_d = [ 0.03,  0.02,  0.02, 0.05 ]
        self.mu    = [ 0.3,   0.0,   0.3,  0.0  ]
        self.tau_a = [ 0.400, 0.001, 0.2,  0.001] # rm 0s: / by 0 in 3rd eq.

        self.setI()
        self.excite = random.choice([True,False])
        self.ye = None
        self.yi = None
        self.yt = None
        # cap the states for quantisation. Use positive domain because ye and yi
        # should always be positive
        # These domains are different because of the way they're used in the
        # output equation; i & t are used directly, e is used inside exp()
        self.edom = (0, 15)
        self.idom = (0, 0.5)
        self.tdom = (0, 0.5)
        self.reset()

    def setI(self):
        'i selects the neuron type from the predefined values'
        self.i = random.randint(0,3)

    def reset(self):
        self.ye = rdom(self.edom, 0, self.quanta)
        self.yi = rdom(self.idom, 0, self.quanta)
        self.yt = rdom(self.tdom, 0, self.quanta)
        self.setOutput()

    def setOutput(self):
        self.output = max(0, 1 - math.e**(self.r[self.i]*(self.theta[self.i] - self.ye)) - self.yi - self.mu[self.i]*self.yt)
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

    def preUpdate(self):
        excite_inputs = [x for x in self.inputs if x.excite]
        inhibit_inputs = [x for x in self.inputs if not x.excite]
        # here we are assuming that all sensory input is excitatory
        DT = 1.0 / 50
        self.next_ye = self.ye + DT * (-self.ye + self.wsum(excite_inputs)) / self.tau_d[self.i]
        self.next_yi = self.yi + DT * (-self.yi + self.wsum(inhibit_inputs, 0)) / self.tau_d[self.i]
        self.next_yt = self.yt + DT * (-self.yt + self.output)/self.tau_a[self.i]
        # restrict state to domain for quantisation
        # yt is (0,0.5) since (0,4) is too big for the decay, and due to direct
        # use of yt in output equation it has a large effect on output.
        self.next_ye = quantiseDomain(self.edom, self.next_ye, self.quanta)
        self.next_yi = quantiseDomain(self.idom, self.next_yi, self.quanta)
        self.next_yt = quantiseDomain(self.tdom, self.next_yt, self.quanta)

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
