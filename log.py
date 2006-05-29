#import sys

#from logging import *
#from os import open
# our loggers are divided into simlog for sim.py and root for everything else

# this gets executed only on the first import

#if type == 'file':
## #    logstream = open('/tmp/client.log', 'wb')
## #elif type == 'stderr':

## ## class MyFilter(Filter):
## ##      def __init__(self,name=''):
## ##          Filter.__init__(self,name)
## ##      def filter(self, record):
## ##          r = Filter.filter(self, record)
## ##          print record.name
## ##          return r

## f = Formatter("%(filename)s(%(lineno)d):%(message)s")

## #devnull=open('/dev/null','w')
## #devnull=sys.stderr
## h = StreamHandler(sys.stderr)
## h.setFormatter(f)
## root.addHandler(h)
## # set log level
## root.setLevel(DEBUG)
## #filter = MyFilter()
## #root.addFilter(filter)
## # init simulator logging
## simlog = getLogger('sim.py')

## # dont send messages to the root logger!
## # otherwise we get everything logged twice
## simlog.propagate = 0

## #h2 = StreamHandler(sys.stderr)
## simlog.addHandler(h)
## simlog.setLevel(INFO)
## # TEST!
## #root.debug('root logging enabled')
## #simlog.debug('sim logging enabled')


## #def logToFile():
## #    global logstream
## #    logstream = open('/tmp/client.log', 'wb')

## # could use this for logs, instead use root log
## #log = logging.getLogger('network.py')
## #log.setLevel(logging.DEBUG)

## # hmm adding this doesnt work -
## #AttributeError: 'builtin_function_or_method' object has no attribute 'filter'
## #class Myfilter(Filter):
## #    def filter(self, record):
## #        return 1
## #filter = MyFilter()
## #root.addFilter(filter)


