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

class Pars(Persistent):
    pass

class Node(Persistent):

    def __init__(self, par):
        self.inputs = PersistentList() # list of internal inputs
        # externalInputs[(bp,sig)] = signalvalue
        self.externalInputs = PersistentMapping()
        # par is a class for all the evolvable parameters of the model. If set
        # in the constructor we can use a central parameter set, otherwise each
        # neuron has its own.
        if par == 0:
            pass
        elif par == 1:
            self.par = Pars()
        else:
            self.par = par

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

    def __init__(self, par, weightDomain=(-7,7), quanta=None, abs_weights=0):
        # with absolute weights and polarity neurons range must be >= 0.
        if abs_weights:
            assert weightDomain[0] >= 0
        Node.__init__(self, par)
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
            if isinstance(src, SrmNode):
                # hack since output is spikes, we want eps function
                # note that we don't do quantisation here.
                x = src.eps
            cumulative += x * self.weights[src]
        if use_external:
            for (src, x) in self.externalInputs.items():
                if self.quanta:
                    x = quantise(x, self.quanta)
                cumulative += x * self.weights[src]
        return cumulative

class SigmoidNode(WeightNode):
    'Sigmoid model (no internal state)'

    def __init__(self, par, weightDomain=(-7,7), quanta=None):
        # we pass on par here even though sigmoid has no internal parameters
        WeightNode.__init__(self, par, weightDomain, quanta)
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

    def __init__(self, par, weightDomain=(-7,7), quanta=None):
        WeightNode.__init__(self, par, weightDomain, quanta)
        self.par.phaseOffset = None
        self.par.stepSize = None
        self.par.amplitude = None
        self.setPhaseOffset()
        self.setStepSize()
        self.reset()
        self.setAmplitude()
        self.postUpdate()

    def setPhaseOffset(self):
        self.par.phaseOffset = rdom((0,2*math.pi), self.par.phaseOffset, self.quanta)

    def setStepSize(self):
        # oscillate between [twice per second, once every 2 seconds)
        persec = math.pi*2/50
        self.par.stepSize = rdom((persec/2, persec*2), self.par.stepSize, self.quanta)

    def reset(self):
        self.state = self.par.phaseOffset

    def setAmplitude(self):
        self.par.amplitude = rdom((0.25, 1), self.par.amplitude, self.quanta)

    def postUpdate(self):
        'return output in [0,1]'
        self.output = quantise((math.sin(self.state)*self.par.amplitude + 1) / 2, self.quanta)
        self.state = (self.state + self.par.stepSize) % (2*math.pi)

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

    def __init__(self, par, weightDomain=(-16,16), quanta=None, biasDomain=(-4,4)):
        WeightNode.__init__(self, par, weightDomain, quanta)
        if par == 1:
            self.par.adaptRate = None
            self.par.bias = None
            self.par.biasDomain = biasDomain
            self.setAdaptRate()
            self.setBias()
        self.state = None
        self.reset()

    def preUpdate(self):
        DT = 1.0 / 50
        self.nextState = self.state + DT * (self.wsum() - self.state) / self.par.adaptRate
        # cap state to [-4,4]. This isn't part of the normal model but we need
        # clear boundaries for quantisation. +-4 is enough to define a clear
        # output range that almost gets to 0 and 1.
        self.nextState = quantiseDomain((-4,4), self.nextState, self.quanta)

    def postUpdate(self):
        self.state = self.nextState
        self.output = 1/(1 + math.e**-(self.state + self.par.bias))
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
        self.par.adaptRate = rdom((0.05,0.5), self.par.adaptRate, self.quanta)

    def setBias(self):
        # suggested value is 2
        self.par.bias = rdom(self.par.biasDomain, self.par.bias, self.quanta)

    def reset(self):
        self.state = rdom((-0.1,0.1), self.state, self.quanta)
        self.output = 1/(1 + math.e**-(self.state + self.par.bias))
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

class IfNode(BeerNode):
    'Integrate-and-fire spiking neuron model'

    def __init__(self, par, weightDomain=(-16,16), quanta=None, biasDomain=(1,4)):
        BeerNode.__init__(self, par, weightDomain, quanta, biasDomain)
        if par == 1:
            self.par.tr = None # refraction time
            self.setTr()

    def setTr(self):
        self.par.tr = random.randint(5,25) # refract cycles (between 0 and 1/2 second)

    def postUpdate(self):
        self.output = 0
        self.t += 1
        if self.t > self.par.tr:
            BeerNode.postUpdate(self)
            # override sigmoid output with spike
            self.output = 0
            if self.state >= self.par.bias: # bias is actually used as firing threshold
                self.state = 0
                self.output = 1
                self.t = 0

    def mutate(self, p):
        mutations = 0
        mutations += BeerNode.mutate(self, p)
        if random.random() < p:
            self.setTr()
            mutations += 1
        return mutations

    def reset(self):
        BeerNode.reset(self)
        self.t = 100 # cycles since last firing

class SrmNode(WeightNode):
    'Spike-response-model'

    def __init__(self, par, weightDomain=(-4,4), quanta=None):
        WeightNode.__init__(self, par, weightDomain, quanta)
        if par == 1:
            self.par.ft = None
            self.setFt()
        self.reset()
        self.etamax=0
        self.etamin=0

    def reset(self):
        self.spikes = []

    def preUpdate(self):
        # 20ms is too small since integration step is this big, so stretch
        # functions to 200ms.
        # we're counting in steps of 20ms upto 200ms, but we scale this to
        # [0,20] for function calls to eps and eta.
        self.spikes = [x+2 for x in self.spikes if x<20]
        self.eps = 0
        self.eta = 0
        for s in self.spikes:
            # we don't need to quantise values here because we could just use a
            # precalculated 10 entry lookup table
            if s >= 2: # synapse delay
                self.eps += math.exp(-(s-2)/4)*(1-math.exp(-(s-2)/10))
            self.eta += -math.exp(-s/4)
        self.eps = quantiseDomain((0,1.0), self.eps, self.quanta)
        self.eta = quantiseDomain((-1.1,0), self.eta, self.quanta)

    def postUpdate(self):
        # wsum() uses neuron.eps for SrmNode neurons
        self.state = quantiseDomain((-4,4), self.wsum() + self.eta, self.quanta)
        self.output = 0
        if self.state > self.par.ft:
            self.spikes = [0] + self.spikes
            self.output = 1

    def setFt(self):
        'firing threshold'
        self.par.ft = rdom((-4,4), self.par.ft, self.quanta)

    def mutate(self, p):
        mutations = 0
        mutations += WeightNode.mutate(self, p)
        if random.random() < p:
            self.setFt()
            mutations += 1
        return mutations

class TagaNode(WeightNode):
    'Taga 2nd order model'

    def __init__(self, par, weightDomain=(-4,4), quanta=None):
        WeightNode.__init__(self, par, weightDomain, quanta)
        if par == 1:
            self.par.tau0 = 0.2 # originally 1.0, but very slow, this seems to work better.
            self.par.tau1 = 0.2 # also 1.0
            self.par.beta = 2.5
            self.par.b = 1.0
        self.reset()

    def reset(self):
        self.u = 0
        self.v = 0
        self.setOutput()

    def setOutput(self):
        self.output = max(0, self.u)

    def preUpdate(self):
        DT = 1.0 / 50
        self.next_u = self.u + DT * (-self.u - self.par.beta*max(0,self.v) + self.wsum() + self.par.b) / self.par.tau0
        self.next_v = self.v + DT * (-self.v + self.output) / self.par.tau1

        self.next_u = quantiseDomain((-1,1), self.next_u, self.quanta)
        self.next_v = quantiseDomain((0,1), self.next_v, self.quanta)

    def postUpdate(self):
        self.u = self.next_u
        self.v = self.next_v
        self.setOutput()

class WallenNode(WeightNode):
    'Wallen 3rd order model'

    def __init__(self, par, weightDomain=(0,16), quanta=None):
        WeightNode.__init__(self, par, weightDomain, quanta, 1)
               # i =    0      1      2     3
        self.theta = [-0.2,   0.1,   0.5,  8.0  ]
        self.r     = [ 1.8,   0.3,   1.0,  0.5  ]
        self.tau_d = [ 0.03,  0.02,  0.02, 0.05 ]
        self.mu    = [ 0.3,   0.0,   0.3,  0.0  ]
        self.tau_a = [ 0.400, 0.001, 0.2,  0.001] # rm 0s: / by 0 in 3rd eq.

        if par == 1:
            self.setI()
        self.par.excite = random.choice([True,False])
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
        self.par.i = random.randint(0,3)

    def reset(self):
        self.ye = rdom(self.edom, 0, self.quanta)
        self.yi = rdom(self.idom, 0, self.quanta)
        self.yt = rdom(self.tdom, 0, self.quanta)
        self.setOutput()

    def setOutput(self):
        self.output = max(0, 1 - math.e**(self.r[self.par.i]*(self.theta[self.par.i] - self.ye)) - self.yi - self.mu[self.par.i]*self.yt)
        if self.quanta:
            self.output = quantise(self.output, self.quanta)

    def preUpdate(self):
        excite_inputs = [x for x in self.inputs if x.par.excite]
        inhibit_inputs = [x for x in self.inputs if not x.par.excite]
        # here we are assuming that all sensory input is excitatory
        DT = 1.0 / 50
        self.next_ye = self.ye + DT * (-self.ye + self.wsum(excite_inputs)) / self.tau_d[self.par.i]
        self.next_yi = self.yi + DT * (-self.yi + self.wsum(inhibit_inputs, 0)) / self.tau_d[self.par.i]
        self.next_yt = self.yt + DT * (-self.yt + self.output)/self.tau_a[self.par.i]
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
            self.par.excite = not self.par.excite
            mutations += 1
        return mutations

class MultiValueLogicFunction(PersistentList):
    """logical function of k inputs. outputs in the domain [low,high]

    Used by Logical node."""

    def __init__(self, numberOfInputs, quanta):
        "Create a new random lookup table"
        PersistentList.__init__(self)
        self.quanta = quanta
        for _ in range(int(round(quanta ** numberOfInputs))):
            self.append(self.getRandomValue())
        log.debug('MultiValueLogicFunction created %d entries', len(self))

    def getRandomValue(self):
        "Returns a random but valid value"
        randomValue = random.randint(0, self.quanta-1)
        return randomValue

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

    def __init__(self, par, numberOfInputs=None, quanta=None):
        "Either use a previously generated function table, or make a new one"
        Node.__init__(self, par)
        if par == 1:
            assert numberOfInputs and quanta
            self.par.function = MultiValueLogicFunction(numberOfInputs, quanta)
        self.reset()

    def reset(self):
        self.nextState = self.par.function.getRandomValue()
        self.postUpdate()

    # The number of inputs can vary dynamically over the course of evolution. At
    # this level we have no way to know how many inputs will be in the eventual
    # phenotype, and yet we're expected to keep a complete lookup table in the
    # genotype. So we keep the lookup table static but allow the bits to
    # overlap, so we'll end up with duplicate bits from the internal and
    # external inputs effectively XORed to partition the input space.
    def preUpdate(self):
        "Convert inputs to a decimal value and lookup in logic function"
        x = 0
        assert self.par.function.quanta**len(self.inputs) == len(self.par.function)
        for i in range(len(self.inputs)):
            # we could just use the input neuron .state instead of .output
            # should get the same value, but without conversion
            v = int(round(self.inputs[i].output*(self.par.function.quanta-1)))
            assert 0 <= v < self.par.function.quanta
            x += self.par.function.quanta**i * v
        assert isinstance(x, int)
        assert x < len(self.par.function)
        # consider external inputs
        # this will roll over the end of the lookup table
        for i in range(len(self.externalInputs)):
            v = self.externalInputs.values()[i]
            assert 0 <= v <= 1
            q = quantise(v, self.par.function.quanta)
            x += self.par.function.quanta**i * int(q*(self.par.function.quanta-1))
        x = x%len(self.par.function)
        self.nextState = self.par.function[x]

    def postUpdate(self):
        self.state = self.nextState
        self.output = float(self.state) / (self.par.function.quanta-1)

    def mutate(self, p):
        "Mutate the function"
        m = self.par.function.mutate(p)
        return m
