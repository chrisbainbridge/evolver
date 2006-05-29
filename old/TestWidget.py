
# PLOTTING DIRECTIONAL HINGES

#                 # rotate to point along a,b,c
#                 # hack for small axis values.. problems with simulation accuracy cause bad rotations
#                 SMALL_NUMBER = 1e-5
#                 if abs(x)<SMALL_NUMBER or abs(y)<SMALL_NUMBER:
#                     zrot = math.pi/2
#                 else:
#                     if x>0 and y>0:
#                         zrot = math.atan(y/x)
#                     elif x<0 and y>0:
#                         zrot = math.pi-math.atan(y/-x)
#                     elif x<0 and y<0:
#                         zrot = math.pi+math.atan(-y/-x)
#                     elif x>0 and y<0:
#                         zrot = 2*math.pi-math.atan(-y/x)

#                 if abs(z)<SMALL_NUMBER or abs(x)<SMALL_NUMBER:
#                     yrot = 0
#                 else:
#                     if x>0 and z>0:
#                         yrot = math.atan(z/x)
#                     elif x<0 and z>0:
#                         yrot = math.pi-math.atan(z/-x)
#                     elif x<0 and z<0:
#                         yrot = math.pi+math.atan(-z/-x)
#                     elif x>0 and z<0:
#                         yrot = 2*math.pi-math.atan(-z/x)
#                 log.debug('HINGE rotate about z,y = %d,%d', math.degrees(zrot), math.degrees(yrot))
#                 glRotate(math.degrees(zrot),0,0,1)
#                 glRotate(math.degrees(yrot),0,1,0)
#                 # FIXME: rotate about yrot
#                 #if debug: print 'HINGE rotate about y:',math.degrees(yrot)
#                 #if not hasattr(self,'myrot'): self.myrot=0
#                 #self.myrot+=1
#                 #glRotate(-self.myrot,0,1,0)

#                 #glRotate(-math.degrees(yrot),0,1,0)
#                 # hinge is sphere extended along x axis
#                 glScale(5,1,1)
#                 glutSphere(0.5,5,5)
#                 #glPopMatrix()
