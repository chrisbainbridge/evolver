"""The main QT application for visualising simulations.

The QApplication is responsible for creating and managing the main
widget (currently qtgui.py) created by qt_designer. The main widget in
turn is responsible for creating and managing the glwidget (currently
TestDidget.py).

Events related to display (rotating, movement, shading etc.) are
handled in glwidget.py. Everything else is passed to the
QApplication here.

The QApplication also steps the simulator and schedules an opengl
redraw whenever it receives a specified timer event.

"""

import tempfile

from qt import *
from qtgl import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
try:
    import qtgui
except ImportError:
    import os
    os.system('make qtgui.py')
    import qtgui

from sim import DT

import logging
log = logging.getLogger('qtapp')

class MyApp(QApplication):
    def __init__(self, args, sim):
        """Initialise QApplication.

        args -- QT flags string
        sim -- simulation to run

        """
        log.debug('myapp init with args %s', args)
        QApplication.__init__(self, args)
        self.sim = sim
        if not QGLFormat.hasOpenGL():
            raise Exception('No Qt OpenGL support.')
        log.debug('We have OpenGL support')
        # create the gui
        self.window = qtgui.QtGui()
        self.window.statusBar().hide()
        self.glwidget = self.window.glwidget
        # tell GL widget what to draw
        self.glwidget.sim = sim
        self.glwidget.qtapp = self
        # set timerEvent for each timestep
        self.startTimer(DT*1000)
        # create main window
        self.setMainWidget(self.window)
        self.window.show()
        # what to do when we quit
        QObject.connect(self, SIGNAL("lastWindowClosed()"), self.quit)
        # default end time
        self.end_time = 0
        self.window.progressBar1.hide()
        self.window.score_label.setText('0')
        self._old_sim_total_time = 0
        self._old_sim_score = 0
        self.window.progressBar1.setTotalSteps(round(self.sim.max_simsecs))
        self.window.progressBar1.show()
        self.steps = 0
        log.debug('end of qtapp init')
        self.frameno = 0

    def destroy(self):
        self.killTimers()
        del self.window
        del self.sim
        del self.glwidget.sim

    def quit(self):
        "Quit the application"
        log.debug('QEEET!')
        # if recording is on, shut it down
        if self.glwidget.record:
            self.window.hide()
            self.glwidget.finaliseRecording()
        QApplication.quit(self)

    def setRecord(self, record, avifile=''):
        """Turn recording on/off and set the output file name.

        record -- 0 for off, 1 for on
        avifile -- file name

        """
        # tell self.glwidget to record movie
        self.glwidget.record = record
        self.glwidget.avifile = avifile
        if self.glwidget.record:
            self.glwidget.screenshot_dir = tempfile.mkdtemp()

    def timerEvent(self, event):
        """Callback from QT event timer."""
        log.debug('qtapp.timerEvent on %s', self)
        # step the ODE simulation
        if not self.glwidget.pause and hasattr(self, 'sim'):
            self.sim.step()
            self.steps += 1
        # we tell it explicitly when to record a frame, otherwise spurious
        # repaints will cause the movie to go out of sync with the physics
        if self.glwidget.record and (self.frameno==0):
            self.glwidget.record_this_frame = 1
        self.frameno = (self.frameno + 1)%5
        # schedule a repaint
        self.glwidget.updateGL()
        # show simulation time counter
        if self.steps % 25 == 0:
            if self.sim.max_simsecs:
                self.window.progressBar1.setProgress(round(self.sim.total_time))
            self.window.score_label.setText('%.1f : %.3f'%(self.sim.total_time, self.sim.score))
        if self.sim.finished:
            self.quit()
