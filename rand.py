import random
from cgkit.cgtypes import vec3
import math

mut = 'uniform'

def rnd(a, b, v):
    if mut == 'gauss' and v != None:
        y = random.gauss(v, 0.5)
        if y<a: y = float(a)
        if y>b: y = float(b)
        return y
    elif mut == 'uniform':
        return random.uniform(a, b)

def randomVec3(ov):
    "Create a random normalised vector"
    try:
        if ov == None:
            ov = (None, None, None)
        v = vec3(rnd(-1,1,ov[0]), rnd(-1,1,ov[1]), rnd(-1,1,ov[2])).normalize()
    except:
        v = vec3(1,0,0)
    return v

def randomQuat(v):
    "Create a random quaternion (vector and angle)"
    if v != None:
        (oldrad, oldvec) = v
    else:
        (oldrad, oldvec) = (None, None)
    rad = rnd(0, 2*math.pi, oldrad)
    vec = randomVec3(oldvec)
    return (rad, tuple(vec))

def randomAxis(v):
    if v == None:
        v = (None, None)
    xyz = vec3(rnd(-1,1,v[0]), rnd(-1,1,v[1]), 0)
    return tuple(xyz.normalize())
