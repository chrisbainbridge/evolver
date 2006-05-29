#!/usr/bin/python

import sys
sys.path = ['/home/chrb/cvs/pyode/build/lib.linux-i686-2.3'] + sys.path
import ode
import gc

#import memprof
#sampler = memprof.Sampler()

#sampler.run()
for i in range(5000):
    w = ode.World()
    body = ode.Body(w)
    # creating geom leads to 'dict' object leaks (_geom_c2py_lut ?)
    geom = ode.GeomCCylinder()
    # setBody leads to 'Body' object leaks
    geom.setBody(body)
    # no 'Body' leak if we set it back to None
    #geom.setBody(None)
    #sampler.run()
    #timestamp = time.time()
    del ode._geom_c2py_lut[geom._id()]
    print ode._geom_c2py_lut
    typeMap = {}
    for obj in gc.get_objects():
        if hasattr(obj, '__class__'):
            t = obj.__class__
        else:
            t = type(obj)
        t = str(getattr(t, '__name__', t))

        typeMap[t] = typeMap.get(t, 0) + 1

    l = []
    for name,count in typeMap.iteritems():
        l.append((name, count))
    l.sort(lambda x,y: cmp(y[1],x[1]))
    print l
# It appears that nothing is ever removed from _geom_c2py_lut. Should be done in __dealloc__ ?
# geomobject __dealloc__ should del self.body ?
