"""Trace neuron activity.

Data file is text, ready for gnuplot etc. Format is:

# header
# 
# time signal1 signal2 ...
#
# 0.0 0.2 1.0 ...
# 0.02 ...
# 0.04 ...

How to use:

from trace import trace
trace.setFile(fname)      # turn on tracing to the given file
trace.declareSignal(str)        # call this for each signal
trace.writeHeader()             # we're done declaring
in sim loop:
trace.setTime(t)                # current sim time
trace.logValue(signal, x)
trace.flushLine()

"""

import logging
log = logging.getLogger('trace')
log.setLevel(logging.WARN)

class SignalLog:
    def __init__(self):
        self.tracing = 0
        self.fd = None
        self.signals = []
        self.time = 0
        self.values = {}

#    def openFile(self, fname):
#        self.fd = open(fname,'wb')
#
#    def setTime(self, time):
#        self.time = time
#
#    def declareSignal(self, signal):
#        self.signals.append(signal)
#
#    def declareSignals(self, signals):
#        self.signals += signals

    def writeHeader(self):
        if self.fd:
            #self.fd.write('# This is a trace log file\n')
            #self.fd.write('# Signal list:\n#\n')
            #self.fd.write('# time ')
            self.fd.write('# signals:')
            for signal in self.signals:
                self.fd.write(' '+signal)
            self.fd.write('\n\n')

#    def logValue(self, signal, value):
#        self.values[signal] = value

    def flushLine(self):
        "Write the line in the order of self.signals"
        # write time
        if self.fd:
            s = str(self.time)
            for signal in self.signals:
                try:
                    value = self.values[signal]
                except KeyError:
                    log.debug('WARNING: value of signal %s not set at time %f. Substituting 0.', signal, self.time)
                    value = 0
                s += ' '+str(value)
            s += '\n'
            self.fd.write(s)
        self.values = {}
