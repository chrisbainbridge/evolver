# removed stuff

def drawGround_grid(self):
  #print 'draw plane',geom.getParams()
  #((a,b,c),d)=geom.getParams()
  # FIXME: we should use the plane eqn above to plot the plane

  # RENDER A LINE GRID
  glColor(0,1,0)
  glBegin(GL_LINES)
  for x in range(-100,100,5):
    glVertex(x,0,-100)
    glVertex(x,0,100)
    glVertex(-100,0,x)
    glVertex(100,0,x)
  glEnd()
  # RENDER A FLAT PLANE
  # front facing is counter clockwise    
  #glBegin(GL_QUADS)
  #glVertex(-100,0,-100)
  #glVertex(100,0,-100)
  #glVertex(100,0,100)
    #glVertex(-100,0,100)
    #glEnd()

  def drawCube(self):
    
    glTranslatef(0.0,0.0,-2.0)
    #glRotatef(90,1.0,0.0,0.0)                     # Rotate The Cube On It's X Axis
    glRotatef(45,0.0,1.0,0.0)                     # Rotate The Cube On It's Y Axis
    #glRotatef(90,0.0,0.0,1.0)            
    glBegin(GL_QUADS)                           # Start Drawing The Cube

    # Front Face (note that the texture's corners have to match the quad's corners)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(-1.0, -1.0,  1.0)    # Bottom Left Of The Texture and Quad
    glTexCoord2f(1.0, 0.0)
    glVertex3f( 1.0, -1.0,  1.0)    # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0)
    glVertex3f( 1.0,  1.0,  1.0)    # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0)
    glVertex3f(-1.0,  1.0,  1.0)    # Top Left Of The Texture and Quad
    
    # Back Face
    glTexCoord2f(1.0, 0.0)
    glVertex3f(-1.0, -1.0, -1.0)    # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0)
    glVertex3f(-1.0,  1.0, -1.0)    # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0)
    glVertex3f( 1.0,  1.0, -1.0)    # Top Left Of The Texture and Quad
    glTexCoord2f(0.0, 0.0)
    glVertex3f( 1.0, -1.0, -1.0)    # Bottom Left Of The Texture and Quad
    
    # Top Face
    glTexCoord2f(0.0, 1.0)
    glVertex3f(-1.0,  1.0, -1.0)    # Top Left Of The Texture and Quad
    glTexCoord2f(0.0, 0.0)
    glVertex3f(-1.0,  1.0,  1.0)    # Bottom Left Of The Texture and Quad
    glTexCoord2f(1.0, 0.0)
    glVertex3f( 1.0,  1.0,  1.0)    # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0)
    glVertex3f( 1.0,  1.0, -1.0)    # Top Right Of The Texture and Quad
    
    # Bottom Face
    glTexCoord2f(1.0, 1.0)
    glVertex3f(-1.0, -1.0, -1.0)    # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0)
    glVertex3f( 1.0, -1.0, -1.0)    # Top Left Of The Texture and Quad
    glTexCoord2f(0.0, 0.0)
    glVertex3f( 1.0, -1.0,  1.0)    # Bottom Left Of The Texture and Quad
    glTexCoord2f(1.0, 0.0)
    glVertex3f(-1.0, -1.0,  1.0)    # Bottom Right Of The Texture and Quad
    
    # Right face
    glTexCoord2f(1.0, 0.0)
    glVertex3f( 1.0, -1.0, -1.0)    # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0)
    glVertex3f( 1.0,  1.0, -1.0)    # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0)
    glVertex3f( 1.0,  1.0,  1.0)    # Top Left Of The Texture and Quad
    glTexCoord2f(0.0, 0.0)
    glVertex3f( 1.0, -1.0,  1.0)    # Bottom Left Of The Texture and Quad
    
    # Left Face
    glTexCoord2f(0.0, 0.0)
    glVertex3f(-1.0, -1.0, -1.0)    # Bottom Left Of The Texture and Quad
    glTexCoord2f(1.0, 0.0)
    glVertex3f(-1.0, -1.0,  1.0)    # Bottom Right Of The Texture and Quad
    glTexCoord2f(1.0, 1.0)
    glVertex3f(-1.0,  1.0,  1.0)    # Top Right Of The Texture and Quad
    glTexCoord2f(0.0, 1.0)
    glVertex3f(-1.0,  1.0, -1.0)    # Top Left Of The Texture and Quad

    glEnd()                                # Done Drawing The Cube

    #glOrtho(-width/2.0,width/2.0,-height/2.0,height/2.0,0.1,200)

    ## this code was supposed to set frustum, but gluPerspective seems to work well
##     w = width / float(height)
##     h = 1.0

##     vnear=0.1
##     vfar=100.0
##     k=0.8 # view scale, 1 = +/- 45 degrees
##     k2=float(height)/width
##     if width>=height:
##       #glFrustum(-1,1,-1,1,1.5,20)
##       glFrustum(-vnear*k,vnear*k,-vnear*k*k2,vnear*k*k2,vnear,vfar)
##     else:
##       glFrustum(-vnear*k*k2,vnear*k*k2,-vnear*k,vnear*k,vnear,vfar)
      

##     glMatrixMode(GL_PROJECTION)
##     glLoadIdentity()
    #glFrustum( -w, w, -h, h, 5.0, 60.0 )

##    glMatrixMode(GL_MODELVIEW)
    #glLoadIdentity()
    #glTranslatef( 0.0, 0.0, -40.0 )

def setTransform(pos,R):
  matrix=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
  matrix[0]=R[0]
  matrix[1]=R[4]
  matrix[2]=R[8]
  matrix[3]=0
  matrix[4]=R[1]
  matrix[5]=R[5]
  matrix[6]=R[9]
  matrix[7]=0
  matrix[8]=R[2]
  matrix[9]=R[6]
  matrix[10]=R[10]
  matrix[11]=0
  matrix[12]=pos[0]
  matrix[13]=pos[1]
  matrix[14]=pos[2]
  matrix[15]=1
  glPushMatrix()
  glMultMatrixf (matrix)


import ZODB, ZODB.FileStorage
db=ZODB.DB(ZODB.FileStorage.FileStorage('evolve.fs', create=0))
root=db.open().root()
e=root['evolver']
dir(e)
