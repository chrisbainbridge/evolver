"""A Qglwidget for rendering the 3D simulation scene.

This widget is embedded within the main widget GUI output by
qt-designer. It provides support for visualising the 3D Geoms,
rotating and moving the viewpoint, turning on/off effects like
wireframe, shading).

This widget can also retrieve the rendered picture from the
framebuffer, allowing screenshots and avi recordings to be
made. Recordings of movie frames have to be synchronised with ODE
simulation steps, not redraws, otherwise the speed will vary when you
do things like moving the mouse over the widget!

"""

import math
import os
import sys

from qt import *
from qtgl import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import ode
from cgkit.cgtypes import vec3, mat3, mat4, vec4
import Image

import logging
log = logging.getLogger('glwidget')

class GLWidget(QGLWidget):

    """An OpenGL widget that renders an ODE scene"""

    def __init__(self, parent=None, name=None):
        log.debug('glwidget init')
        QGLWidget.__init__(self, parent, name)
        # make sure all key events come here
        self.grabKeyboard()
        # camera x,y,z
        self.view_xyz = [0,-30,5]
        # camera heading,pitch,roll
        self.view_hpr = [90,20,0]
        self.pause = 1
        self.drag_left = 0
        self.drag_right = 0
        self.drag_middle = 0
        self.use_textures = 1
        self.smooth_shaded = 1
        self.lighting = 1
        self.sky_offset = 0.0
        self.tracking = 1
        self.track_obj = None
        self.old_view_xyz = self.view_xyz
        # stuff for movies
        self.frame = 0
        self.record_this_frame = 0
        self.record = 0
        self.render_bps = 1
        self.render_axes = 0
        self.wireframe = 0
        self.fullscreen = 0

    def initializeGL(self):
        log.debug('initialiseGL')
        self.quadratic = gluNewQuadric()
        gluQuadricNormals(self.quadratic, GLU_SMOOTH)
        gluQuadricTexture(self.quadratic, GL_TRUE)
        self.loadTextures()
        glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGBA|GLUT_DEPTH)
        log.debug('double buffer: %d',self.doubleBuffer())
        log.debug('auto buffer swap: %d',self.autoBufferSwap())

        glViewport(0,0,800,600)
        # Initialize
        glClearColor(0.694,0.866,1.0,0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        # Light sources
        glEnable(GL_LIGHTING)
        glLight(GL_LIGHT0,GL_POSITION,[20,-20,20,0])
        glLight(GL_LIGHT0,GL_DIFFUSE,[1,1,1,1])
        glLight(GL_LIGHT0,GL_SPECULAR,[1,1,1,1])
        glEnable(GL_LIGHT0)
        glLightModel(GL_LIGHT_MODEL_LOCAL_VIEWER,GL_TRUE)
        glLightModel(GL_LIGHT_MODEL_AMBIENT,(0.2,0.2,0.2))
        glMaterial(GL_FRONT,GL_SPECULAR,(0.0,0.1,0.1,1))
        glMaterial(GL_FRONT,GL_SHININESS,50.0)
        # enable back face culling
        # - make sure all front faces are counter clockwise
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        # color affects front facing triangles with ambient
        # and diffuse light
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT,GL_AMBIENT_AND_DIFFUSE)

    def reset(self):
        log.debug('in reset')
        if hasattr(self,'reset_callback'):
            self.reset_callback()
        else:
            log.debug('reset callback not defined!')

    def reset_callback(self):
        """Override this to do something useful on reset."""
        pass

    def loadTextures(self):
        # set pixel unpacking mode
        glPixelStorei(GL_UNPACK_SWAP_BYTES, 0)
        glPixelStorei(GL_UNPACK_ROW_LENGTH, 0)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glPixelStorei(GL_UNPACK_SKIP_ROWS, 0)
        glPixelStorei(GL_UNPACK_SKIP_PIXELS, 0)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
        # create the textures
        class Texture:
            pass
        self.images = {}
        for name in 'ground','sky':
            im = Image.open(name+'.ppm')
            self.images[name] = Texture()
            self.images[name].data = im.tostring("raw", "RGBX", 0, -1)
            self.images[name].x = im.size[0]
            self.images[name].y = im.size[1]
            self.images[name].handle = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D,self.images[name].handle)
            gluBuild2DMipmaps(GL_TEXTURE_2D, 3, im.size[0], im.size[1], GL_RGBA, GL_UNSIGNED_BYTE, self.images[name].data)

    def wrapCameraAngles(self):
        for i in range(0,3):
            while (self.view_hpr[i] > 180): self.view_hpr[i] -= 360
            while (self.view_hpr[i] < -180): self.view_hpr[i] += 360

    def setCamera(self):
        # rotate view so ground is x,y plane, we are looking along y increasing
        # into the distance, and z increases vertically upwards
        if self.tracking and self.track_obj:
            obj_xyz = self.track_obj.getPosition()
            if not hasattr(self,'old_obj_xyz'):
                self.old_obj_xyz = obj_xyz
            else:
                difference = (obj_xyz[0]-self.old_obj_xyz[0],obj_xyz[1]-self.old_obj_xyz[1],obj_xyz[2]-self.old_obj_xyz[2])
                #if debug: print 'obj moved by',difference
                self.old_obj_xyz = obj_xyz
                self.view_xyz[0] += difference[0]
                self.view_xyz[1] += difference[1]
                self.view_xyz[2] += difference[2]

        # translate to camera x,y,z and rotate to orientation defined by
        # camera heading, pitch and roll
        x = self.view_xyz[0]
        y = self.view_xyz[1]
        z = self.view_xyz[2]
        h = self.view_hpr[0]
        p = self.view_hpr[1]
        r = self.view_hpr[2]
        glMatrixMode (GL_MODELVIEW)
        glLoadIdentity()
        glRotatef (90, 0,0,1)
        glRotatef (90, 0,1,0)
        glRotatef (r, 1,0,0)
        glRotatef (p, 0,1,0)
        glRotatef (-h, 0,0,1)
        glTranslatef (-x,-y,-z)

    def drawSky(self):
        glDisable(GL_LIGHTING)
        if self.use_textures:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D,self.images['sky'].handle)
        else:
            glDisable(GL_TEXTURE_2D)
            glColor(0.694,0.866,1.0)

        # make sure sky depth is as far back as possible
        glShadeModel(GL_FLAT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glDepthRange(1,1)

        ssize = 1000.0
        sky_scale = 1.0/4.0
        sky_height = 1.0
        x = ssize*sky_scale
        z = self.view_xyz[2] + sky_height

        glBegin(GL_QUADS)
        glNormal3f (0,0,-1)
        glTexCoord2f (-x+self.sky_offset, -x+self.sky_offset)
        glVertex3f (-ssize+self.view_xyz[0], -ssize+self.view_xyz[1], z)
        glTexCoord2f (-x+self.sky_offset, x+self.sky_offset)
        glVertex3f (-ssize+self.view_xyz[0], ssize+self.view_xyz[1], z)
        glTexCoord2f (x+self.sky_offset, x+self.sky_offset)
        glVertex3f (ssize+self.view_xyz[0], ssize+self.view_xyz[1], z)
        glTexCoord2f (x+self.sky_offset, -x+self.sky_offset)
        glVertex3f (ssize+self.view_xyz[0], -ssize+self.view_xyz[1], z)
        glEnd()

        # reset everything back
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)
        self.sky_offset = self.sky_offset + 0.002
        if (self.sky_offset > 1): self.sky_offset -= 1
        glDepthFunc (GL_LESS)
        glDepthRange (0,1)

    def drawGround(self):
        glDisable (GL_LIGHTING)
        glShadeModel (GL_FLAT)
        glEnable (GL_DEPTH_TEST)
        glDepthFunc (GL_LESS)

        if self.use_textures:
            glEnable (GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D,self.images['ground'].handle)
        else:
            glDisable(GL_TEXTURE_2D)
            glColor(0.5,0.5,0.3)

        gsize = 1000.0 # size of ground is -gsize..+gsize
        offset = 0.0 # vertical offset
        ground_scale = 1.0
        ground_ofsx = 0.0 # ground centered around origin
        ground_ofsy = 0.0

        glBegin (GL_QUADS)
        glNormal3f (0,0,1)
        glTexCoord2f (-gsize*ground_scale + ground_ofsx,
                      -gsize*ground_scale + ground_ofsy)
        glVertex3f (-gsize,-gsize,offset)
        glTexCoord2f (gsize*ground_scale + ground_ofsx,
                      -gsize*ground_scale + ground_ofsy)
        glVertex3f (gsize,-gsize,offset)
        glTexCoord2f (gsize*ground_scale + ground_ofsx,
                      gsize*ground_scale + ground_ofsy)
        glVertex3f (gsize,gsize,offset)
        glTexCoord2f (-gsize*ground_scale + ground_ofsx,
                      gsize*ground_scale + ground_ofsy)
        glVertex3f (-gsize,gsize,offset)
        glEnd()
        
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)

    def plotAxes(self):
        "Plot x,y,z axes at current position and rotation"
        if self.render_axes:
            glColor(1,0,0)
            glDisable(GL_LIGHTING)
            glBegin(GL_LINES)
            glVertex(0,0,0)
            glVertex(5,0,0)
            glEnd()
            glColor(0,1,0)
            glBegin(GL_LINES)
            glVertex(0,0,0)
            glVertex(0,5,0)
            glEnd()
            glColor(0,0,1)
            glBegin(GL_LINES)
            glVertex(0,0,0)
            glVertex(0,0,5)
            glEnd()
            glEnable(GL_LIGHTING)

    def shadeAndLight(self):
        if self.smooth_shaded:
            glShadeModel(GL_SMOOTH)
        else:
            glShadeModel(GL_FLAT)
        if self.lighting:
            glEnable(GL_LIGHTING)
        else:
            glDisable(GL_LIGHTING)

    def renderJoints(self):
        # Render Joints 
        for joint in self.sim.joints:
            log.debug('drawing joint %s',str(joint)) #name)
            glPushMatrix()

            if type(joint) is ode.HingeJoint:

                (x0,y0,z0) = joint.getBody(0).getPosition()
                (x1,y1,z1) = joint.getBody(1).getPosition()
                (x,y,z) = joint.getAnchor()
                # draw green lines between the joint and bodies
                glColor(0,1,0)
                glDisable(GL_LIGHTING)
                glBegin(GL_LINES)
                glVertex(x0,y0,z0)
                glVertex(x,y,z)
                glVertex(x,y,z)
                glVertex(x1,y1,z1)
                glEnd()
                glEnable(GL_LIGHTING)
                # draw extended sphere for joint
                glColor(1,1,1)
                glTranslate(x,y,z)
                x,y,z = joint.getAxis()
                log.debug('HINGE axis %f,%f,%f',x,y,z)
                glColor(1,1,1)
                glDisable(GL_LIGHTING)
                glBegin(GL_LINES)
                glVertex(0,0,0)
                glVertex(x*5,y*5,z*5)
                glEnd()
                glEnable(GL_LIGHTING)
                
            elif type(joint) is ode.UniversalJoint:

                (x0,y0,z0) = joint.getAxis1()
                (x1,y1,z1) = joint.getAxis2()
                (x,y,z) = joint.getAnchor()
                # draw green lines between the joint and bodies
                glColor(0.0,0.0,0.0)
                glDisable(GL_LIGHTING)
                glBegin(GL_LINES)
                glVertex(x,y,z)
                glVertex(x+x0,y+y0,z+z0)
                glVertex(x,y,z)
                glVertex(x+x1,y+y1,z+z1)
                glEnd()
                glEnable(GL_LIGHTING)
                # draw extended sphere for joint
                log.debug('HINGE axis %f,%f,%f',x,y,z)

            elif type(joint) is ode.SliderJoint:
                log.debug('slider: draw sliderjoint')
                # draw a line between the limits
                point = joint.getPosition()
                axis = vec3(joint.getAxis())
                log.debug('slider: point %f, axis %f',point,axis)
                b = joint.getBody(0)
                p = vec3(b.getPosition())
                log.debug('slider: x,y,z=%f,%f,%f',x,y,z)
                # xyz is positition, axis is gradient...
                lowstop = joint.getParam(ode.ParamLoStop)
                highstop = joint.getParam(ode.ParamHiStop)
                log.debug('slider: lowstop=%f,highstop=%f',lowstop, highstop)
                a = p-axis*100
                b = p+axis*100
                glColor(0,0,0)
                glDisable(GL_LIGHTING)
                glBegin(GL_LINES)
                glVertex(a[0],a[1],a[2])
                glVertex(b[0],b[1],b[2])
                glEnd()
                glEnable(GL_LIGHTING)

            elif type(joint) is ode.BallJoint:
                log.debug('render ode.BallJoint')
                # render the axes
                m = joint.motor
                a0 = vec3(m.getAxis(0))
                p = vec3(joint.getBody(0).getPosition())
                glColor(1,0,0)
                glDisable(GL_LIGHTING)
                glBegin(GL_LINES)
                glVertex(p[0],p[1],p[2])
                q = p+a0
                glVertex(q[0],q[1],q[2])
                glEnd()
                glColor(0,1,0)
                glBegin(GL_LINES)
                glVertex(0,0,0)
                glVertex(0,5,0)
                glEnd()
                glColor(0,0,1)
                glBegin(GL_LINES)
                glVertex(0,0,0)
                glVertex(0,0,5)
                glEnd()
                glEnable(GL_LIGHTING)

            else:
                log.debug('dont know how to render joint %s', str(joint))
            # restore matrix
            glPopMatrix()

    def renderGeoms(self):
        # Render Geoms
        log.debug('rendering %d geoms', self.sim.space.getNumGeoms())

        if self.wireframe:
            gluQuadricDrawStyle(self.quadratic, GLU_SILHOUETTE)
        else:
            gluQuadricDrawStyle(self.quadratic, GLU_FILL)
            

        for i in range(self.sim.space.getNumGeoms()):
            geom = self.sim.space.getGeom(i)

            glPushMatrix()

            if type(geom) is ode.GeomSphere:
                log.debug('draw sphere')
                glColor(0,0,1)
                x,y,z = geom.getPosition()
                glTranslate(x,y,z)
                glutSolidSphere(geom.getRadius(),20,20)
            elif type(geom) is ode.GeomPlane:
                pass

            elif type(geom) is ode.GeomBox:
                log.debug('draw box(%s) @(%s)',str(geom.getLengths()),str(geom.getPosition()))
                glColor(0.8,0,0)
                x,y,z = geom.getPosition()
                # create openGL 4x4 transform matrix from ODE 3x3 rotation matrix
                R = geom.getRotation()
                log.debug('ROTATE = %s',str(R)) # R is a 3x3 matrix
                T = mat4()
                T.setMat3(mat3(R))
                T.setColumn(3, vec4(x, y, z, 1.0))
                glMultMatrixd(T.toList())
                (sx,sy,sz) = geom.getLengths()
                log.debug('size (%f,%f,%f)', sx, sy, sz)
                glScale(sx,sy,sz)
                if self.wireframe:
                    glutWireCube(1)
                else:
                    glutSolidCube(1)

            elif type(geom) is ode.GeomCCylinder:
                log.debug('draw ccylinder')
                # construct transformation matrix from position and rotation
                x,y,z = geom.getPosition()
                rotmat = mat3(geom.getRotation())
                log.debug('r=%s', geom.getRotation())
                # ode ccylinders are aligned along z axis by default
                T = mat4()
                T.setMat3(rotmat)
                T.setColumn(3, vec4(x, y, z, 1.0))
                log.debug('geom matrix T is %s', str(T))
                glMultMatrixd(T.toList())
                (radius, length) = geom.getParams()
                log.debug('geom len=%f xyz=%f,%f,%f', length, x, y, z)

                # plot the geom
                self.plotAxes()
                if self.render_bps:
                    glTranslate(0, 0, -length/2)
                    if hasattr(geom, 'root'):
                        glColor(0.0, 0.5, 0.5)
                    else:
                        glColor(0, 0, 0.8)
                    gluCylinder(self.quadratic, radius, radius, length, 16, 16)
                    if geom.left == 'internal':
                        glColor(0, 1, 0)
                    else:
                        glColor(1,0,0)
                    gluSphere(self.quadratic, radius, 10, 10)
                    glTranslate(0, 0, length)
                    if geom.right == 'internal':
                        glColor(0, 1, 0)
                    else:
                        glColor(1,0,0)
                    gluSphere(self.quadratic, radius, 10, 10)

            else:
                log.critical('dont know how to render geom %s', str(geom))

            glPopMatrix()

    def paintGL(self):
        log.debug('paintGL')

        self.setCamera()
        glClear( GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
        self.drawSky()
        self.drawGround()
        self.shadeAndLight()
        self.plotAxes() # at origin
#        self.renderJoints()
        self.renderGeoms()
        glFlush()
        # take a screenshot
        if self.record_this_frame:
            self.record_this_frame = 0
            self.screenshot()

    def keyPressEvent(self,e):
        if e.text() == 'r':
            log.debug('key r')
            self.reset()
        elif e.text() == 'c':
            self.screenshot(single=1)
        elif e.text() == 'f':
            self.fullscreen ^= 1
            if self.fullscreen:
                self.qtapp.window.showFullScreen()
            else:
                self.qtapp.window.showNormal()
        elif e.key() == Qt.Key_Up:
            self.view_xyz[1] += 0.1
        elif e.key() == Qt.Key_Down:
            self.view_xyz[1]-=0.1
        elif e.key() == Qt.Key_Left:
            self.view_xyz[0]-=0.1
        elif e.key() == Qt.Key_Right:
            self.view_xyz[0] += 0.1
        elif e.text() == 's':
            self.qtapp.sim.step()
            self.updateGL()
        elif e.text() == 'l':
            self.lighting ^= 1
        elif e.text() == 't':
            self.use_textures ^= 1
        elif e.text() == 'p':
            self.pause ^= 1
        elif e.text() == 'x':
            self.render_bps ^= 1
        elif e.text() == 'a':
            self.render_axes ^= 1
        elif e.text() == 'w':
            self.wireframe ^= 1
        else:
            e.ignore()

    def mousePressEvent(self,e):
        log.debug('mouse press event: button %s',str(e.button()))
        self.old_xy_point = (e.pos().x(),e.pos().y())
        if e.button() == Qt.LeftButton:
            self.drag_left = 1
        elif e.button() == Qt.RightButton:
            self.drag_right = 1
        elif e.button() == Qt.MidButton:
            self.drag_middle = 1

    def mouseReleaseEvent(self,e):
        self.drag_left = 0
        self.drag_right = 0
        self.drag_middle = 0

    def mouseMoveEvent(self,e):
        log.debug('mouseMoveEvent')
        scale = 0.02
        pos = e.pos()
        x = int(str(pos.x()))
        y = int(str(pos.y()))

        if not hasattr(self, 'old_xy_point'):
            # huh? mouse press event doesn't arrive first?
            return
        deltax = (x-self.old_xy_point[0])
        deltay = (y-self.old_xy_point[1])
        log.debug('MOUSE: move by (%d,%d)',deltax,deltay)

        self.old_xy_point = (x,y)

        side = scale * float(deltax)
        s = float( math.sin (math.radians(self.view_hpr[0])))
        c = float( math.cos (math.radians(self.view_hpr[0])))
        if self.drag_left == 1:
            self.view_hpr[0] += float (deltax) * 0.5
            self.view_hpr[1] += float (deltay) * 0.5
        elif self.drag_right or self.drag_middle:
            if self.drag_right == 1:
                fwd = scale * float(deltay)
            elif self.drag_middle == 1:
                fwd = 0.0
            self.view_xyz[0] += -s*side + c*fwd
            self.view_xyz[1] += c*side + s*fwd
            if self.drag_middle: self.view_xyz[2] += scale * float(deltay)
            log.debug('MOUSE: NEW X,Y,Z IS %d,%d,%d',self.view_xyz[0],self.view_xyz[1],self.view_xyz[2])

        self.wrapCameraAngles()

    def resizeGL(self,width,height):
        log.debug('resize')
        glViewport( 0, 0, width, height )
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(90,width/float(height),0.1,250)

    def getViewport(self):
        viewport = glGetIntegerv(GL_VIEWPORT)
        x = viewport[0]
        y = viewport[1]
        width = viewport[2]
        height = viewport[3]
        return (x, y, width, height)

    def screenshot(self, single=0):
        "Save the currently rendered framebuffer to a .png file"
        (x,y,w,h) = self.getViewport()
        log.debug('screenshot x,y,width,height = %d,%d,%d,%d', x, y, w, h)
        img = self.grabFrameBuffer()
        if single:
            fname = 'screenshot.jpg'
        else:
            fname = self.screenshot_dir+'/shot-'+str(self.frame).zfill(5)+'.jpg'
        img.save(fname, 'JPEG', 90)
        self.frame += 1

    def finaliseRecording(self):
        "Turn all of the frames into a mpeg4 movie"
        assert(self.record)
        log.debug('glwidget.finaliseRecording')
        
        _,_,width,height = self.getViewport()
        # 2-pass xvid encoding at 160kbit
        cmd0 = 'mencoder mf://%s/*.jpg'\
               ' -mf type=jpg:fps=10 '%(self.screenshot_dir)
        cmd1a = ' -ovc lavc -lavcopts vcodec=mpeg4:vpass=1'
        cmd1b = ' -ovc lavc -lavcopts vcodec=mpeg4:mbd=2:trell:vpass=2'
        cmd2 =  ' -oac copy'\
                ' -o %s'%(self.avifile)
        for c1 in cmd1a, cmd1b:
            cmd = cmd0 + c1 + cmd2
            if log.level != logging.DEBUG:
                cmd += ' &> /dev/null'
            log.debug('executing %s', cmd)
            res = os.system(cmd)
            if res:
                log.critical('cmd fail: %s', cmd)
                sys.exit(res)

        # erase all of the tmp files
        cmd = ('rm -rf ' + self.screenshot_dir)
        log.debug('%s',cmd)
        os.system(cmd)

