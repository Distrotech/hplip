# -*- coding: utf-8 -*-
#
# (c) Copyright 2001-2009 Hewlett-Packard Development Company, L.P.
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


# Local
from base.g import *
from base import device, utils
from prnt import cups
from base.codes import *
from ui_utils import *
from installer.core_install import CoreInstall
from installer.core_install import  PLUGIN_INSTALL_ERROR_NONE, \
                                    PLUGIN_INSTALL_ERROR_PLUGIN_FILE_NOT_FOUND, \
                                    PLUGIN_INSTALL_ERROR_DIGITAL_SIG_NOT_FOUND, \
                                    PLUGIN_INSTALL_ERROR_DIGITAL_SIG_BAD, \
                                    PLUGIN_INSTALL_ERROR_PLUGIN_FILE_CHECKSUM_ERROR, \
                                    PLUGIN_INSTALL_ERROR_NO_NETWORK, \
                                    PLUGIN_INSTALL_ERROR_DIRECTORY_ERROR, \
                                    PLUGIN_INSTALL_ERROR_UNABLE_TO_RECV_KEYS,  \
                                    MODE_CHECK

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from plugindialog_base import Ui_Dialog


PAGE_SOURCE = 0
# PAGE_LICENSE = 1 # part of plug-in itself, this is a placeholder
PAGE_MAX = 1



class PluginDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, install_mode=PLUGIN_NONE, plugin_reason=PLUGIN_REASON_NONE):
        QDialog.__init__(self, parent)
        self.install_mode = install_mode
        self.plugin_reason = plugin_reason
        self.plugin_path = None
        self.result = False
        self.core = CoreInstall(MODE_CHECK)
        self.core.set_plugin_version()
        self.setupUi(self)

        self.user_settings = UserSettings()
        self.user_settings.load()
        self.user_settings.debug()

        self.initUi()

        QTimer.singleShot(0, self.showSourcePage)


    def isPluginInstalled(self):
        return self.core.check_for_plugin()


    def initUi(self):
        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)

        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('hp_logo', '128x128')))

        self.PLUGIN_REASON_TEXT = {
            PLUGIN_REASON_NONE: None,
            PLUGIN_REASON_PRINTING_SUPPORT: self.__tr("This plugin will enable printing support."),
            PLUGIN_REASON_FASTER_PRINTING: self.__tr("This plugin will enhance print speed."),
            PLUGIN_REASON_BETTER_PRINTING_PQ: self.__tr("This plugin will enhance print quality."),
            PLUGIN_REASON_PRINTING_FEATURES: self.__tr("This plugin will add printing features."),
            PLUGIN_REASON_RESERVED_10: None,
            PLUGIN_REASON_RESERVED_20: None,
            PLUGIN_REASON_SCANNING_SUPPORT: self.__tr("This plugin will enable scanning support."),
            PLUGIN_REASON_FASTER_SCANNING: self.__tr("This plugin will enhance scanning speed."),
            PLUGIN_REASON_BETTER_SCANNING_IQ: self.__tr("This plugin will enhance scanning image quality."),
            PLUGIN_REASON_RESERVED_200: None,
            PLUGIN_REASON_RESERVED_400: None,
            PLUGIN_REASON_FAXING_SUPPORT: self.__tr("This plugin will enable faxing support."),
            PLUGIN_REASON_FAX_FEATURES: self.__tr("This plugin will enhnace faxing features."),
            PLUGIN_REASON_RESERVED_20000: None,
            PLUGIN_REASON_RESERVED_40000: None,
        }

    #
    # SOURCE PAGE
    #
    def showSourcePage(self):
        reason_text = self.plugin_reason_text()

        if reason_text is not None:
            if self.install_mode == PLUGIN_REQUIRED:
                self.TitleLabel.setText(self.__tr("An additional driver plug-in is required to operate this printer. You may download the plug-in directly from an HP authorized server (recommended), or, if you already have a copy of the file, you can specify a path to the file (advanced). <br><br>%1").arg(reason_text))
                self.SkipRadioButton.setEnabled(False)

            elif self.install_mode == PLUGIN_OPTIONAL:
                self.TitleLabel.setText(self.__tr("An optional driver plug-in is available to enhance the operation of this printer. You may download the plug-in directly from an HP authorized server (recommended), skip this installation (not recommended), or, if you already have a copy of the file, you can specify a path to the file (advanced).<br><br>%1").arg(reason_text))

        self.connect(self.DownloadRadioButton, SIGNAL("toggled(bool)"), self.DownloadRadioButton_toggled)
        self.connect(self.CopyRadioButton, SIGNAL("toggled(bool)"), self.CopyRadioButton_toggled)
        self.connect(self.SkipRadioButton, SIGNAL("toggled(bool)"), self.SkipRadioButton_toggled)
        self.connect(self.PathLineEdit, SIGNAL("textChanged(const QString &)"), self.PathLineEdit_textChanged)
        self.connect(self.BrowseToolButton, SIGNAL("clicked()"), self.BrowseToolButton_clicked)

        self.BrowseToolButton.setIcon(QIcon(load_pixmap('folder_open', '16x16')))

        self.displayPage(PAGE_SOURCE)


    def DownloadRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(False)
            self.BrowseToolButton.setEnabled(False)
            self.NextButton.setEnabled(True)
            try:
                self.PathLineEdit.setStyleSheet("")
            except AttributeError:
                pass
            self.plugin_path = None


    def CopyRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(True)
            self.BrowseToolButton.setEnabled(True)
            self.plugin_path = unicode(self.PathLineEdit.text())
            self.setPathIndicators()


    def SkipRadioButton_toggled(self, b):
        if b:
            self.PathLineEdit.setEnabled(False)
            self.BrowseToolButton.setEnabled(False)
            self.NextButton.setEnabled(True)
            try:
                self.PathLineEdit.setStyleSheet("")
            except AttributeError:
                pass
            self.plugin_path = None


    def PathLineEdit_textChanged(self, t):
        self.plugin_path = unicode(t)
        self.setPathIndicators()


    def setPathIndicators(self):
        ok = True
        if not self.plugin_path or (self.plugin_path and os.path.isdir(self.plugin_path)):
            self.PathLineEdit.setToolTip(self.__tr("You must specify a path to the '%1' file.").arg(self.core.plugin_name))
            ok = False
        elif os.path.basename(self.plugin_path) != self.core.plugin_name:
            self.PathLineEdit.setToolTip(self.__tr("The plugin filename must be '%1'.").arg(self.core.plugin_name))
            ok = False

        if not ok:
            try:
                self.PathLineEdit.setStyleSheet("background-color: yellow; ")
            except AttributeError:
                pass
            self.NextButton.setEnabled(False)
        else:
            try:
                self.PathLineEdit.setStyleSheet("")
            except AttributeError:
                pass
            self.NextButton.setEnabled(True)
            self.PathLineEdit.setToolTip(QString(""))


    def BrowseToolButton_clicked(self):
        t = unicode(self.PathLineEdit.text())

        if not os.path.exists(t):
            path = unicode(QFileDialog.getOpenFileName(self, self.__tr("Select Plug-in File"),
                                                #user_conf.workingDirectory(),
                                                self.user_settings.working_dir,
                                                self.__tr("Plugin Files (*.run)")))

        if path:
            self.plugin_path = path
            self.PathLineEdit.setText(self.plugin_path)
            #user_conf.setWorkingDirectory(self.plugin_path)
            self.user_settings.working_dir = self.plugin_path
            self.user_settings.save()

        self.setPathIndicators()

    #
    # Misc
    #

    def displayPage(self, page):
        self.updateStepText(page)
        self.StackedWidget.setCurrentIndex(page)


    def CancelButton_clicked(self):
        self.close()


    def NextButton_clicked(self):
        if self.SkipRadioButton.isChecked():
            log.debug("Skipping plug-in installation.")
            self.close()
            return

        beginWaitCursor()
        try:

            if self.plugin_path is None: # download
                # read plugin.conf (local or on sf.net) to get plugin_path (http://)
                plugin_conf_url = self.core.get_plugin_conf_url()

                if plugin_conf_url.startswith('file://'):
                    pass
                else:
                    log.info("Checking for network connection...")
                    ok = self.core.check_network_connection()

                    if not ok:
                        log.error("Network connection not detected.")
                        endWaitCursor()
                        FailureUI(self, self.__tr("Network connection not detected."))
                        self.close()
                        return

                log.info("Downloading configuration file from: %s" % plugin_conf_url)
                self.plugin_path, size, checksum, timestamp, ok = self.core.get_plugin_info(plugin_conf_url,
                    self.plugin_download_callback)

                log.debug("path=%s, size=%d, checksum=%s, timestamp=%f, ok=%s" %
                        (self.plugin_path, size, checksum, timestamp, ok))

                if not self.plugin_path.startswith('http://') and not self.plugin_path.startswith('file://'):
                    self.plugin_path = 'file://' + self.plugin_path

            else: # path
                if not self.plugin_path.startswith('http://'):
                    self.plugin_path = 'file://' + self.plugin_path

                size, checksum, timestamp = 0, '', 0

            if self.plugin_path.startswith('file://'):
                pass
            else:
                log.info("Checking for network connection...")
                ok = self.core.check_network_connection()

                if not ok:
                    log.error("Network connection not detected.")
                    endWaitCursor()
                    FailureUI(self, self.__tr("Network connection not detected."))
                    self.close()
                    return

            log.info("Downloading plug-in from: %s" % self.plugin_path)

            status, ret = self.core.download_plugin(self.plugin_path, size, checksum, timestamp,
                self.plugin_download_callback)

            if status in (PLUGIN_INSTALL_ERROR_UNABLE_TO_RECV_KEYS, PLUGIN_INSTALL_ERROR_DIGITAL_SIG_NOT_FOUND):
                endWaitCursor()
                if QMessageBox.question(self, self.__tr("Digital signature download failed"),
                        self.__tr("<b>The download of the digital signature file failed.</b><p>Without this file, it is not possible to authenticate and validate the plug-in prior to installation.</p>Do you still want to install the plug-in?"),
                        QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:

                    self.core.delete_plugin()
                    self.close()
                    return

            elif status != PLUGIN_INSTALL_ERROR_NONE:

                if status == PLUGIN_INSTALL_ERROR_PLUGIN_FILE_NOT_FOUND:
                    desc = self.__tr("<b>ERROR: Plug-in file not found (server returned 404 or similar error).</b><p>Error code: %1</p>").arg(str(ret))

                elif status == PLUGIN_INSTALL_ERROR_DIGITAL_SIG_BAD:
                    desc = self.__tr("<b>ERROR: Plug-in file does not match its digital signature.</b><p>File may have been corrupted or altered.</p><p>Error code: %1</p>").arg(str(ret))

                elif status == PLUGIN_INSTALL_ERROR_PLUGIN_FILE_CHECKSUM_ERROR:
                    desc = self.__tr("<b>ERROR: Plug-in file does not match its checksum. File may have been corrupted or altered.")

                elif status == PLUGIN_INSTALL_ERROR_NO_NETWORK:
                    desc = self.__tr("<b>ERROR: Unable to connect to network to download the plug-in.</b><p>Please check your network connection and try again.</p>")

                elif status == PLUGIN_INSTALL_ERROR_DIRECTORY_ERROR:
                    desc = self.__tr("<b>ERROR: Unable to create the plug-in directory.</b><p>Please check your permissions and try again.</p>")

                self.core.delete_plugin()
                endWaitCursor()
                FailureUI(self, desc)
                self.close()
                return

            if not self.core.run_plugin(GUI_MODE, self.plugin_install_callback):
                self.core.delete_plugin()
                endWaitCursor()
                FailureUI(self, self.__tr("Plug-in install failed."))
                self.close()
                return

            cups_devices = device.getSupportedCUPSDevices(['hp'])
            for dev in cups_devices:
                mq = device.queryModelByURI(dev)

                if mq.get('fw-download', False):
                    # Download firmware if needed
                    log.info(log.bold("\nDownloading firmware to device %s..." % dev))
                    try:
                        d = None
                        try:
                            d = device.Device(dev)
                        except Error:
                            log.error("Error opening device.")
                            endWaitCursor()
                            FailureUI(self, self.__tr("<b>Firmware download to device failed.</b><p>%1</p>").arg(dev))
                            continue

                        if d.downloadFirmware():
                            log.info("Firmware download successful.\n")
                        else:
                            endWaitCursor()
                            FailureUI(self, self.__tr("<b>Firmware download to device failed.</b><p>%1</p>").arg(dev))

                    finally:
                        if d is not None:
                            d.close()
        finally:
            endWaitCursor()

        self.core.delete_plugin()
        SuccessUI(self, self.__tr("<b>Plug-in installation successful.</b>"))
        self.result = True
        self.close()


    def plugin_download_callback(self, c, s, t):
        pass


    def plugin_install_callback(self, s):
        print s


    def updateStepText(self, p):
        self.StepText.setText(self.__tr("Step %1 of %2").arg(p+1).arg(PAGE_MAX+1))


    def plugin_reason_text(self):
        try:
            return self.PLUGIN_REASON_TEXT[self.plugin_reason]
        except KeyError:
            return None


    def __tr(self,s,c = None):
        return qApp.translate("PluginDialog",s,c)


