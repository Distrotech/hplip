# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2008 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
# Authors: Don Welch
#

# StdLib
import operator

# Local
from base.g import *
from base import device, utils, maint
from prnt import cups
from base.codes import *
from ui_utils import *

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from cleandialog_base import Ui_Dialog


CLEAN_TYPE_INITIAL = 1000
CLEAN_TYPE_TEST = 1001

PAGE_START = 0
PAGE_LEVEL_1 = 1
PAGE_LEVEL_2 = 2
PAGE_LEVEL_3 = 3
PAGE_FRONT_PANEL = 4

BUTTON_CLEAN = 0
BUTTON_NEXT = 1
BUTTON_FINISH = 2


#d = None
def true():
    return True



class CleanDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, device_uri):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.device_uri = device_uri
        self.clean_type = CLEAN_TYPE_INITIAL
        self.abort = False
        self.seq_index = 0
        self.step = 1
        self.step_max = 0

        self.max_steps = {
                      CLEAN_TYPE_UNSUPPORTED : 1,
                      CLEAN_TYPE_PCL : 4,
                      CLEAN_TYPE_LIDIL : 4,
                      CLEAN_TYPE_PCL_WITH_PRINTOUT : 4,
                    }

        self.seq = { # (func|method, tuple of params|None)
                    CLEAN_TYPE_INITIAL: [ # (used when starting up and clean-type isn't known)
                               (self.showStartPage, None),
                               (self.endStartPage, None), # switch to a valid clean-type here
                            ],

                    CLEAN_TYPE_UNSUPPORTED : [
                                (self.showFrontPanelPage, None),
                                (self.endFrontPanelPage, None),
                                (self.close, None),
                            ],

                    CLEAN_TYPE_PCL : [ # 1
                            (self.showLevel1Page, None),
                            (self.endLevel1Page, None),
                            (self.doClean, (1,)),
                            (self.showLevel2Page, None),
                            (self.endLevel2Page, None),
                            (self.doClean, (2,)),
                            (self.showLevel3Page, None),
                            (self.endLevel3Page, None),
                            (self.doClean, (3,)),
                            (self.close, None),
                            ],

                    CLEAN_TYPE_LIDIL : [  # 2
                            (self.showLevel1Page, None),
                            (self.endLevel1Page, None),
                            (self.doClean, (1,)),
                            (self.showLevel2Page, None),
                            (self.endLevel2Page, None),
                            (self.doClean, (2,)),
                            (self.showLevel3Page, None),
                            (self.endLevel3Page, None),
                            (self.doClean, (3,)),
                            (self.close, None),
                            ],

                    CLEAN_TYPE_PCL_WITH_PRINTOUT : [ # 3
                            (self.showLevel1Page, None),
                            (self.endLevel1Page, None),
                            (self.doClean, (1,)),
                            (self.showLevel2Page, None),
                            (self.endLevel2Page, None),
                            (self.doClean, (2,)),
                            (self.showLevel3Page, None),
                            (self.endLevel3Page, None),
                            (self.doClean, (3,)),
                            # TODO: Add print-out
                            (self.close, None),
                            ],
                    }


        self.initUi()
        QTimer.singleShot(0, self.nextSequence)


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_noDevices"), self.DeviceUriComboBox_noDevices)
        self.connect(self.DeviceComboBox, SIGNAL("DeviceUriComboBox_currentChanged"), self.DeviceUriComboBox_currentChanged)
        self.DeviceComboBox.setFilter({'clean-type': (operator.ne, CLEAN_TYPE_NONE)})

        if self.device_uri:
            self.DeviceComboBox.setInitialDevice(self.device_uri)

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('hp_logo', '128x128')))


    def NextButton_clicked(self):
        self.nextSequence()


    def nextSequence(self):
        while True:
            try:
                seq, params = self.seq[self.clean_type][self.seq_index]
            except IndexError:
                break

            if seq is None:
                self.seq_index += 1
                continue

            self.new_page = False

            t = []
            if params is not None:
                for p in params:
                    try:
                        t.append(p())
                    except:
                        t.append(p)

            try:
                log.debug("%s(%s)" % (seq.func_name, ','.join([repr(x) for x in t])))
            except AttributeError:
                pass

            try:
                seq(*t)
            except Error:
                CheckDeviceUI(self)
                break

            self.seq_index += 1

            if self.new_page:
                break

            if self.abort:
                self.close()


    def showStartPage(self):
        self.setCleanButton(BUTTON_NEXT)
        num_devices = self.DeviceComboBox.setDevices()

        if num_devices == 1:
            self.skipPage()
            return

        self.DeviceComboBox.updateUi()
        self.displayPage(PAGE_START)


    def endStartPage(self):
        self.mq = device.queryModelByURI(self.device_uri)
        self.clean_type = self.mq.get('clean-type', CLEAN_TYPE_NONE)
        self.seq_index = -1

        log.debug("clean-type=%d" % self.clean_type)
        self.step_max = self.max_steps[self.clean_type]

        try:
            self.dev = device.Device(self.device_uri)
        except Error:
            CheckDeviceUI(self)
            return


    def showLevel1Page(self):
        self.setCleanButton(BUTTON_CLEAN)
        self.displayPage(PAGE_LEVEL_1)


    def endLevel1Page(self):
        pass


    def showLevel2Page(self):
        self.displayPage(PAGE_LEVEL_2)


    def endLevel2Page(self):
        pass


    def showLevel3Page(self):
        self.displayPage(PAGE_LEVEL_3)


    def endLevel3Page(self):
        pass


    def showFrontPanelPage(self):
        self.setCleanButton(BUTTON_FINISH)
        self.displayPage(PAGE_FRONT_PANEL)


    def endFrontPanelPage(self):
        pass


    def DeviceUriComboBox_currentChanged(self, device_uri):
        self.device_uri = device_uri


    def DeviceUriComboBox_noDevices(self):
        FailureUI(self, self.__tr("<b>No devices that support print cartridge cleaning found.</b><p>Click <i>OK</i> to exit.</p>"))
        self.close()


    def CancelButton_clicked(self):
        self.close()


    def doClean(self, level):
        try:
            try:
                self.dev.open()
            except Error:
                CheckDeviceUI(self)
            else:
                if self.dev.isIdleAndNoError():
                    if self.clean_type in (CLEAN_TYPE_PCL, # 1
                                      CLEAN_TYPE_PCL_WITH_PRINTOUT): # 3

                        if level == 1:
                            maint.cleanType1(self.dev)

                        elif level == 2:
                            maint.primeType1(self.dev)

                        else: # 3
                            maint.wipeAndSpitType1(self.dev)


                    elif self.clean_type == CLEAN_TYPE_LIDIL: # 2
                        if level == 1:
                            maint.cleanType2(self.dev)

                        elif level == 2:
                            maint.primeType2(self.dev)

                        else: # 3
                            maint.wipeAndSpitType2(self.dev)

                    maint.print_clean_test_page(self.dev)

                else:
                    CheckDeviceUI(self)

        finally:
            if self.dev is not None:
                self.dev.close()


    #
    # Misc
    #

    def displayPage(self, page):
        self.updateStepText(self.step)
        self.step += 1
        self.new_page = True
        self.StackedWidget.setCurrentIndex(page)


    def skipPage(self):
        self.step += 1
        self.new_page = False


    def updateStepText(self, p=None):
        if p is None or not self.step_max:
            self.StepText.setText(QString(""))
        else:
            self.StepText.setText(self.__tr("Step %1 of %2").arg(p).arg(self.step_max))


    def setCleanButton(self, typ=BUTTON_CLEAN):
        if typ == BUTTON_CLEAN:
            self.NextButton.setText(self.__tr("Clean"))
        elif typ == BUTTON_NEXT:
            self.NextButton.setText(self.__tr("Next >"))
        elif typ == BUTTON_FINISH:
            self.NextButton.setText(self.__tr("Finish"))


    def __tr(self,s,c = None):
        return qApp.translate("CleanDialog",s,c)


