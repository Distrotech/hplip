# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2009 Hewlett-Packard Development Company, L.P.
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
# Author: Don Welch
#

from base.g import *
from base import device
from installer import core_install
from installer.core_install import  PLUGIN_INSTALL_ERROR_NONE, \
                                    PLUGIN_INSTALL_ERROR_PLUGIN_FILE_NOT_FOUND, \
                                    PLUGIN_INSTALL_ERROR_DIGITAL_SIG_NOT_FOUND, \
                                    PLUGIN_INSTALL_ERROR_DIGITAL_SIG_BAD, \
                                    PLUGIN_INSTALL_ERROR_PLUGIN_FILE_CHECKSUM_ERROR, \
                                    PLUGIN_INSTALL_ERROR_NO_NETWORK, \
                                    PLUGIN_INSTALL_ERROR_DIRECTORY_ERROR, \
                                    PLUGIN_INSTALL_ERROR_UNABLE_TO_RECV_KEYS 

from qt import *
from pluginform2_base import PluginForm2_base

class PluginForm2(PluginForm2_base):
    def __init__(self,parent = None,name = None,modal = 0,fl = 0):
        PluginForm2_base.__init__(self,parent,name,modal,fl)
        self.path = None
        self.version = prop.installed_version
        self.bg = self.pathLineEdit.paletteBackgroundColor()

        self.titleTextLabel.setFont(QFont('Helvetica', 16))

        self.sourceGroup.emit(SIGNAL("clicked(int)"), (0,))

    def sourceGroup_clicked(self, item):
        self.pathLineEdit.setEnabled(item == 1)
        self.browsePushButton.setEnabled(item == 1)

        if item == 0: # download
            QToolTip.remove(self.pathLineEdit)
            self.actionPushButton.setText(self.__tr("Download and Install"))
            self.actionPushButton.setEnabled(True)
            self.path = None
        else: # path
            self.path = unicode(self.pathLineEdit.text())
            self.pathLineEdit.emit(SIGNAL("textChanged(const QString&)"), (self.path,))

            if self.path.startswith(u"http://"):
                self.actionPushButton.setText(self.__tr("Download and Install"))
            else:
                self.actionPushButton.setText(self.__tr("Copy and Install"))


    def browsePushButton_clicked(self):
        dlg = QFileDialog(user_conf.workingDirectory(), self.__tr("HPLIP %s Plug-in (*.run)" %
            self.version), None, None, True)

        dlg.setCaption("openfile")
        dlg.setMode(QFileDialog.ExistingFile)
        dlg.show()

        if dlg.exec_loop() == QDialog.Accepted:
            results = dlg.selectedFile()
            working_directory = unicode(dlg.dir().absPath())
            log.debug("results: %s" % results)
            user_conf.setWorkingDirectory(working_directory)

            if results:
                self.path = unicode(results)
                self.pathLineEdit.setText(self.path)


    def pathLineEdit_textChanged(self, path):
        path, ok = unicode(path), True

        if not path.startswith(u'http://'):
            self.actionPushButton.setText(self.__tr("Copy and Install"))

            if not path or not os.path.exists(path):
                QToolTip.add(self.pathLineEdit, self.__tr('File not found.'))
                ok = False

            elif os.path.basename(path) != u'hplip-%s-plugin.run' % self.version:
                log.error("Incorrect file: %s (should be: %s)" % (path, 'hplip-%s-plugin.run' % self.version))
                QToolTip.add(self.pathLineEdit, self.__tr("Incorrect file. Must be '%1'")\
                    .arg('hplip-%s-plugin.run' % self.version))

                ok = False

        else:
            self.actionPushButton.setText(self.__tr("Download and Install"))

        self.actionPushButton.setEnabled(ok)

        if not ok:
            self.pathLineEdit.setPaletteBackgroundColor(QColor(0xff, 0x99, 0x99))

        else:
            QToolTip.remove(self.pathLineEdit)
            self.pathLineEdit.setPaletteBackgroundColor(self.bg)
            self.path = path


    def actionPushButton_clicked(self):
        core = core_install.CoreInstall(core_install.MODE_CHECK)
        core.set_plugin_version() #self.version)

        if self.path is None: # download
            # read plugin.conf (local or on sf.net) to get plugin_path (http://)
            plugin_conf_url = core.get_plugin_conf_url()

            if plugin_conf_url.startswith('file://'):
                pass
            else:
                pass

                log.info("Checking for network connection...")
                ok = core.check_network_connection()

                if not ok:
                    log.error("Network connection not detected.")
                    self.FailureUI(self.__tr("Network connection not detected."))
                    self.close()
                    return


            log.info("Downloading configuration file from: %s" % plugin_conf_url)

            self.path, size, checksum, timestamp, ok = core.get_plugin_info(plugin_conf_url,
                self.plugin_download_callback)

            log.debug("path=%s, size=%d, checksum=%s, timestamp=%f, ok=%s" %
                    (self.path, size, checksum, timestamp, ok))

            if not self.path.startswith('http://') and not self.path.startswith('file://'):
                self.path = 'file://' + self.path


        else: # path
            if not self.path.startswith('http://'):
                self.path = 'file://' + self.path

            size, checksum, timestamp = 0, '', 0


        if self.path.startswith('file://'):
            pass
        else:

            log.info("Checking for network connection...")
            ok = core.check_network_connection()

            if not ok:
                log.error("Network connection not detected.")
                self.FailureUI(self.__tr("Network connection not detected."))
                self.close()
                return

        log.info("Downloading plug-in from: %s" % self.path)

        status, ret = core.download_plugin(self.path, size, checksum, timestamp,
            self.plugin_download_callback)

        if status != PLUGIN_INSTALL_ERROR_NONE:

            if status == PLUGIN_INSTALL_ERROR_PLUGIN_FILE_NOT_FOUND:
                desc = self.__tr("<b>ERROR: Plug-in file not found (server returned 404 or similar error).</b><p>Error code: %1</p>").arg(str(ret))

            elif status == PLUGIN_INSTALL_ERROR_DIGITAL_SIG_NOT_FOUND:
                desc = self.__tr("<b>ERROR: Plug-in digital signature file not found (server returned 404 or similar error).</b><p>Error code: %1</p>").arg(str(ret))

            elif status == PLUGIN_INSTALL_ERROR_DIGITAL_SIG_BAD:
                desc = self.__tr("<b>ERROR: Plug-in file does not match its digital signature.</b><p>File may have been corrupted or altered.</p><p>Error code: %1</p>").arg(str(ret))

            elif status == PLUGIN_INSTALL_ERROR_PLUGIN_FILE_CHECKSUM_ERROR:
                desc = self.__tr("<b>ERROR: Plug-in file does not match its checksum. File may have been corrupted or altered.")

            elif status == PLUGIN_INSTALL_ERROR_NO_NETWORK:
                desc = self.__tr("<b>ERROR: Unable to connect to network to download the plug-in.</b><p>Please check your network connection and try again.</p>")

            elif status == PLUGIN_INSTALL_ERROR_DIRECTORY_ERROR:
                desc = self.__tr("<b>ERROR: Unable to create the plug-in directory.</b><p>Please check your permissions and try again.</p>")

            elif status == PLUGIN_INSTALL_ERROR_UNABLE_TO_RECV_KEYS:
                desc = self.__tr("<b>ERROR: Unable to download the public HPLIP keys from the keyserver.</b><p>Error code: %1</p>").arg(str(ret))

            core.delete_plugin()
            self.FailureUI(desc)
            self.close()
            return

        local_plugin = ret

        if not core.run_plugin(GUI_MODE, self.plugin_install_callback):
            core.delete_plugin()
            self.FailureUI(self.__tr("Plug-in install failed."))
            self.close()
            return

        cups_devices = device.getSupportedCUPSDevices(['hp']) #, 'hpfax'])

        for dev in cups_devices:
            mq = device.queryModelByURI(dev)

            if mq.get('fw-download', False):

                # Download firmware if needed
                log.info(log.bold("\nDownloading firmware to device %s..." % dev))
                try:
                    d = device.Device(dev)
                except Error:
                    log.error("Error opening device.")
                    continue

                if d.downloadFirmware():
                    log.info("Firmware download successful.\n")

                d.close()


        core.delete_plugin()
        self.SuccessUI("Plug-in install successful.")
        self.close()


    def FailureUI(self, error_text):
        QMessageBox.critical(self,
            self.caption(),
            error_text,
            QMessageBox.Ok,
            QMessageBox.NoButton,
            QMessageBox.NoButton)

    def SuccessUI(self, text):
        QMessageBox.information(self,
                             self.caption(),
                             text,
                              QMessageBox.Ok,
                              QMessageBox.NoButton,
                              QMessageBox.NoButton)



    def plugin_download_callback(self, c, s, t):
        pass


    def plugin_install_callback(self, s):
        print s


    def cancelPushButton_clicked(self):
        self.close()


    def __tr(self,s,c = None):
        return qApp.translate("PluginForm_base",s,c)
