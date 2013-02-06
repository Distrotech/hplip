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
# Authors: Don Welch, Naga Samrat Chowdary Narla
#

# StdLib
import socket
import operator
import commands

# Local
from base.g import *
from base import device, utils, models, pkit
from prnt import cups
from base.codes import *
from ui_utils import *
#from installer import core_install
from installer.core_install import CoreInstall,\
                                   MODE_CHECK

# Qt
from PyQt4.QtCore import *
from PyQt4.QtGui import *

# Ui
from setupdialog_base import Ui_Dialog
from plugindialog import PluginDialog
from wifisetupdialog import WifiSetupDialog, SUCCESS_CONNECTED

# Fax
try:
    from fax import fax
    fax_import_ok = True
except ImportError:
    # This can fail on Python < 2.3 due to the datetime module
    fax_import_ok = False
    log.warning("Fax setup disabled - Python 2.3+ required.")


PAGE_DISCOVERY = 0
PAGE_DEVICES = 1
PAGE_ADD_PRINTER = 2
PAGE_REMOVE = 3


BUTTON_NEXT = 0
BUTTON_FINISH = 1
BUTTON_ADD_PRINTER = 2
BUTTON_REMOVE = 3

ADVANCED_SHOW = 0
ADVANCED_HIDE = 1

DEVICE_DESC_ALL = 0
DEVICE_DESC_SINGLE_FUNC = 1
DEVICE_DESC_MULTI_FUNC = 2





class PasswordDialog(QDialog):
    def __init__(self, prompt, parent=None, name=None, modal=0, fl=0):
        QDialog.__init__(self, parent)
        # Application icon
        self.setWindowIcon(QIcon(load_pixmap('hp_logo', '128x128')))
        self.prompt = prompt

        Layout= QGridLayout(self)
        Layout.setMargin(11)
        Layout.setSpacing(6)

        self.PromptTextLabel = QLabel(self)
        Layout.addWidget(self.PromptTextLabel,0,0,1,3)

        self.UsernameTextLabel = QLabel(self)
        Layout.addWidget(self.UsernameTextLabel,1,0)

        self.UsernameLineEdit = QLineEdit(self)
        self.UsernameLineEdit.setEchoMode(QLineEdit.Normal)
        Layout.addWidget(self.UsernameLineEdit,1,1,1,2)

        self.PasswordTextLabel = QLabel(self)
        Layout.addWidget(self.PasswordTextLabel,2,0)

        self.PasswordLineEdit = QLineEdit(self)
        self.PasswordLineEdit.setEchoMode(QLineEdit.Password)
        Layout.addWidget(self.PasswordLineEdit,2,1,1,2)

        self.OkPushButton = QPushButton(self)
        Layout.addWidget(self.OkPushButton,3,2)

        self.languageChange()

        self.resize(QSize(420,163).expandedTo(self.minimumSizeHint()))

        self.connect(self.OkPushButton, SIGNAL("clicked()"), self.accept)
        self.connect(self.PasswordLineEdit, SIGNAL("returnPressed()"), self.accept)

    def setDefaultUsername(self, defUser, allowUsernameEdit = True):
        self.UsernameLineEdit.setText(defUser)
        if not allowUsernameEdit:
            self.UsernameLineEdit.setReadOnly(True)
            self.UsernameLineEdit.setStyleSheet("QLineEdit {background-color: lightgray}")
    
    def getUsername(self):
        return unicode(self.UsernameLineEdit.text())


    def getPassword(self):
        return unicode(self.PasswordLineEdit.text())


    def languageChange(self):
        self.setWindowTitle(self.__tr("HP Device Manager - Enter Username/Password"))
        self.PromptTextLabel.setText(self.__tr(self.prompt))
        self.UsernameTextLabel.setText(self.__tr("Username:"))
        self.PasswordTextLabel.setText(self.__tr("Password:"))
        self.OkPushButton.setText(self.__tr("OK"))


    def __tr(self,s,c = None):
        return qApp.translate("SetupDialog",s,c)



def showPasswordUI(prompt, userName=None, allowUsernameEdit=True):
    try:	
        dlg = PasswordDialog(prompt, None)

        if userName != None:
            dlg.setDefaultUsername(userName, allowUsernameEdit)

        if dlg.exec_() == QDialog.Accepted:
            return (dlg.getUsername(), dlg.getPassword())

    finally:
        pass

    return ("", "")



class DeviceTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, device_uri):
        QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
        self.device_uri = device_uri



class SetupDialog(QDialog, Ui_Dialog):
    def __init__(self, parent, param, jd_port, device_uri=None, remove=False):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.param = param
        self.jd_port = jd_port
        self.device_uri = device_uri
        self.remove = remove

        if device_uri:
            log.info("Using device: %s" % device_uri)

        self.initUi()

        if self.remove:
            QTimer.singleShot(0, self.showRemovePage)
        else:
            if self.skip_discovery:
                QTimer.singleShot(0, self.showDevicesPage)
            else:
                QTimer.singleShot(0, self.showDiscoveryPage)

        cups.setPasswordCallback(showPasswordUI)


    #
    # INIT
    #

    def initUi(self):
        self.setWindowIcon(QIcon(load_pixmap('hp_logo', '128x128')))

        # connect signals/slots
        self.connect(self.CancelButton, SIGNAL("clicked()"), self.CancelButton_clicked)
        self.connect(self.BackButton, SIGNAL("clicked()"), self.BackButton_clicked)
        self.connect(self.NextButton, SIGNAL("clicked()"), self.NextButton_clicked)
        self.connect(self.ManualGroupBox,  SIGNAL("clicked(bool)"),  self.ManualGroupBox_clicked)

        if self.remove:
            self.initRemovePage()
            self.max_page = 1
        else:
            self.initDiscoveryPage()
            self.initDevicesPage()
            self.initAddPrinterPage()
            self.max_page = PAGE_ADD_PRINTER

    #
    #  DISCOVERY PAGE
    #

    def initDiscoveryPage(self):
        self.UsbRadioButton.setChecked(True)
        self.setUsbRadioButton(True)
        self.ManualGroupBox.setChecked(False)

        self.advanced = False
        self.manual = False
        self.skip_discovery = False
        self.discovery_method = 0
        self.NetworkRadioButton.setEnabled(prop.net_build)
        self.WirelessButton.setEnabled(prop.net_build)
        self.ParallelRadioButton.setEnabled(prop.par_build)
        self.devices = {}
        self.bus = 'usb'
        self.timeout = 5
        self.ttl = 4
        self.search = ''
        self.print_test_page = False
        self.device_desc = DEVICE_DESC_ALL

        if self.param:
            log.info("Searching for device...")
            self.manual = True
            self.advanced = True
            self.ManualParamLineEdit.setText(self.param)
            self.JetDirectSpinBox.setValue(self.jd_port)
            self.ManualGroupBox.setChecked(True)
            self.DiscoveryOptionsGroupBox.setEnabled(False)

            if self.manualDiscovery():
                self.skip_discovery = True
            else:
                FailureUI(self, self.__tr("<b>Device not found.</b> <p>Please make sure your printer is properly connected and powered-on."))

                match = device.usb_pat.match(self.param)
                if match is not None:
                    self.UsbRadioButton.setChecked(True)
                    self.setUsbRadioButton(True)

                else:
                    match = device.dev_pat.match(self.param)
                    if match is not None and prop.par_build:
                        self.ParallelRadioButton.setChecked(True)
                        self.setParallelRadioButton(True)

                    else:
                        match = device.ip_pat.match(self.param)
                        if match is not None and prop.net_build:
                            self.NetworkRadioButton.setChecked(True)
                            self.setNetworkRadioButton(True)

                        else:
                            FailureUI(self, self.__tr("<b>Invalid manual discovery parameter.</b>"))

        elif self.device_uri: # If device URI specified on the command line, skip discovery
                              # if the device URI is well-formed (but not necessarily valid)
            try:
                back_end, is_hp, self.bus, model, serial, dev_file, host, zc, port = \
                device.parseDeviceURI(self.device_uri)

            except Error:
                log.error("Invalid device URI specified: %s" % self.device_uri)

            else:
                name = host
                if self.bus == 'net':
                    try:
                        log.debug("Trying to get hostname for device...")
                        name = socket.gethostbyaddr(host)[0]
                    except socket.herror:
                        log.debug("Failed.")
                    else:
                        log.debug("Host name=%s" % name)

                self.devices = {self.device_uri : (model, model, name)}
                self.skip_discovery = True

        # If no network or parallel, usb is only option, skip initial page...
        elif not prop.par_build and not prop.net_build:
            self.skip_discovery = True
            self.bus = 'usb'
            self.UsbRadioButton.setChecked(True)
            self.setUsbRadioButton(True)

        if prop.fax_build and prop.scan_build:
            self.DeviceTypeComboBox.addItem("All devices/printers", QVariant(DEVICE_DESC_ALL))
            self.DeviceTypeComboBox.addItem("Single function printers only", QVariant(DEVICE_DESC_SINGLE_FUNC))
            self.DeviceTypeComboBox.addItem("All-in-one/MFP devices only", QVariant(DEVICE_DESC_MULTI_FUNC))
        else:
            self.DeviceTypeComboBox.setEnabled(False)

        self.connect(self.AdvancedButton, SIGNAL("clicked()"), self.AdvancedButton_clicked)
        self.connect(self.UsbRadioButton, SIGNAL("toggled(bool)"), self.UsbRadioButton_toggled)
        self.connect(self.NetworkRadioButton, SIGNAL("toggled(bool)"), self.NetworkRadioButton_toggled)
        self.connect(self.WirelessButton, SIGNAL("toggled(bool)"), self.WirelessButton_toggled)
        self.connect(self.ParallelRadioButton, SIGNAL("toggled(bool)"), self.ParallelRadioButton_toggled)
        self.connect(self.NetworkTTLSpinBox,  SIGNAL("valueChanged(int)"), self.NetworkTTLSpinBox_valueChanged)
        self.connect(self.NetworkTimeoutSpinBox,  SIGNAL("valueChanged(int)"),
                     self.NetworkTimeoutSpinBox_valueChanged)
        self.connect(self.ManualGroupBox,  SIGNAL("toggled(bool)"),  self.ManualGroupBox_toggled)

        self.showAdvanced()


    def ManualGroupBox_toggled(self, checked):
        self.DiscoveryOptionsGroupBox.setEnabled(not checked)


    def manualDiscovery(self):
        # Validate param...
        device_uri, sane_uri, fax_uri = device.makeURI(self.param, self.jd_port)

        if device_uri:
            log.info("Found device: %s" % device_uri)
            back_end, is_hp, bus, model, serial, dev_file, host, zc, port = \
                device.parseDeviceURI(device_uri)

            name = host
            if bus == 'net':
                try:
                    name = socket.gethostbyaddr(host)[0]
                except (socket.herror, socket.gaierror):
                    pass

            self.devices = {device_uri : (model, model, name)}

            if bus == 'usb':
                self.UsbRadioButton.setChecked(True)
                self.setUsbRadioButton(True)

            elif bus == 'net' and prop.net_build:
                self.NetworkRadioButton.setChecked(True)
                self.setNetworkRadioButton(True)

            elif bus == 'par' and prop.par_build:
                self.ParallelRadioButton.setChecked(True)
                self.setParallelRadioButton(True)

            return True


        return False


    def ManualGroupBox_clicked(self, checked):
        self.manual = checked
        network = self.NetworkRadioButton.isChecked()
        self.setJetDirect(network)


    def showDiscoveryPage(self):
        self.BackButton.setEnabled(False)
        self.NextButton.setEnabled(True)
        self.setNextButton(BUTTON_NEXT)
        self.displayPage(PAGE_DISCOVERY)


    def AdvancedButton_clicked(self):
        self.advanced = not self.advanced
        self.showAdvanced()


    def showAdvanced(self):
        if self.advanced:
            self.AdvancedStackedWidget.setCurrentIndex(ADVANCED_SHOW)
            self.AdvancedButton.setText(self.__tr("Hide Advanced Options"))
            self.AdvancedButton.setIcon(QIcon(load_pixmap("minus", "16x16")))
        else:
            self.AdvancedStackedWidget.setCurrentIndex(ADVANCED_HIDE)
            self.AdvancedButton.setText(self.__tr("Show Advanced Options"))
            self.AdvancedButton.setIcon(QIcon(load_pixmap("plus", "16x16")))


    def setJetDirect(self, enabled):
        self.JetDirectLabel.setEnabled(enabled and self.manual)
        self.JetDirectSpinBox.setEnabled(enabled and self.manual)


    def setNetworkOptions(self,  enabled):
        self.NetworkTimeoutLabel.setEnabled(enabled)
        self.NetworkTimeoutSpinBox.setEnabled(enabled)
        self.NetworkTTLLabel.setEnabled(enabled)
        self.NetworkTTLSpinBox.setEnabled(enabled)


    def setSearchOptions(self, enabled):
        self.SearchLineEdit.setEnabled(enabled)
        self.DeviceTypeComboBox.setEnabled(enabled)
        self.DeviceTypeLabel.setEnabled(enabled)


    def setManualDiscovery(self, enabled):
        self.ManualGroupBox.setEnabled(enabled)


    def setNetworkDiscovery(self, enabled):
        self.NetworkDiscoveryMethodLabel.setEnabled(enabled)
        self.NetworkDiscoveryMethodComboBox.setEnabled(enabled)
        self.NetworkDiscoveryMethodComboBox.setCurrentIndex(1)


    def UsbRadioButton_toggled(self, radio_enabled):
        self.setUsbRadioButton(radio_enabled)


    def setUsbRadioButton(self, checked):
        self.setNetworkDiscovery(not checked)
        self.setJetDirect(not checked)
        self.setNetworkOptions(not checked)
        self.setSearchOptions(checked)
        self.setManualDiscovery(checked)

        if checked:
            self.ManualParamLabel.setText(self.__tr("USB bus ID:device ID (bbb:ddd):"))
            self.bus = 'usb'
            # TODO: Set bbb:ddd validator


    def NetworkRadioButton_toggled(self, radio_enabled):
        self.setNetworkRadioButton(radio_enabled)


    def setNetworkRadioButton(self, checked):
        self.setNetworkDiscovery(checked)
        self.setJetDirect(checked)
        self.setNetworkOptions(checked)
        self.setSearchOptions(checked)
        self.setManualDiscovery(checked)


        if checked:
            self.ManualParamLabel.setText(self.__tr("IP Address or network name:"))
            self.bus = 'net'
            # TODO: Reset validator

    def WirelessButton_toggled(self, radio_enabled):
        self.setWirelessButton(radio_enabled)


    def setWirelessButton(self, checked):
        self.setNetworkDiscovery(not checked)
        self.setJetDirect(not checked)
        self.setNetworkOptions(not checked)
        self.setSearchOptions(not checked)
        self.setManualDiscovery(not checked)


        if checked:
            self.ManualParamLabel.setText(self.__tr("IP Address or network name:"))
            self.bus = 'net'


    def ParallelRadioButton_toggled(self, radio_enabled):
        self.setParallelRadioButton(radio_enabled)


    def setParallelRadioButton(self, checked):
        self.setNetworkDiscovery(not checked)
        self.setJetDirect(not checked)
        self.setNetworkOptions(not checked)
        self.setSearchOptions(not checked)
        self.setManualDiscovery(not checked)


        if checked:
            self.ManualParamLabel.setText(self.__tr("Device node (/dev/...):"))
            self.bus = 'par'
            # TODO: Set /dev/... validator


    def NetworkTTLSpinBox_valueChanged(self, ttl):
        self.ttl = ttl


    def NetworkTimeoutSpinBox_valueChanged(self, timeout):
        self.timeout = timeout

    #
    # DEVICES PAGE
    #

    def initDevicesPage(self):
        self.connect(self.RefreshButton,  SIGNAL("clicked()"),  self.RefreshButton_clicked)


    def showDevicesPage(self):
        self.BackButton.setEnabled(True)
        self.setNextButton(BUTTON_NEXT)
        search = ""

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            if not self.devices:
                if self.manual and self.param: # manual, but not passed-in on command line
                    self.manualDiscovery()

                else: # probe
                    net_search_type = ''

                    if self.bus == 'net':
                        if self.discovery_method == 0:
                            net_search_type = "slp"
                        else:
                            net_search_type = "mdns"

                        log.info("Searching... (bus=%s, timeout=%d, ttl=%d, search=%s desc=%d, method=%s)" %
                                 (self.bus,  self.timeout, self.ttl, self.search or "(None)",
                                  self.device_desc, net_search_type))
                    else:
                        log.info("Searching... (bus=%s, search=%s, desc=%d)" %
                                 (self.bus,  self.search or "(None)", self.device_desc))

                    if self.device_desc == DEVICE_DESC_SINGLE_FUNC:
                        filter_dict = {'scan-type' : (operator.le, SCAN_TYPE_NONE)}

                    elif self.device_desc == DEVICE_DESC_MULTI_FUNC:
                        filter_dict = {'scan-type': (operator.gt, SCAN_TYPE_NONE)}

                    else: # DEVICE_DESC_ALL
                        filter_dict = {}

                    self.devices = device.probeDevices([self.bus], self.timeout, self.ttl,
                                                       filter_dict, self.search, net_search=net_search_type)
        finally:
            QApplication.restoreOverrideCursor()

        self.clearDevicesTable()

        if self.devices:
            self.NextButton.setEnabled(True)
            self.DevicesFoundIcon.setPixmap(load_pixmap('info', '16x16'))

            if len(self.devices) == 1:
                self.DevicesFoundLabel.setText(self.__tr("<b>1 device found.</b> Click <i>Next</i> to continue."))
            else:
                self.DevicesFoundLabel.setText(self.__tr("<b>%1 devices found.</b> Select the device to install and click <i>Next</i> to continue.").arg(len(self.devices)))

            self.loadDevicesTable()

        else:
            self.NextButton.setEnabled(False)
            self.DevicesFoundIcon.setPixmap(load_pixmap('error', '16x16'))
            log.error("No devices found on bus: %s" % self.bus)
            self.DevicesFoundLabel.setText(self.__tr("<b>No devices found.</b><br>Click <i>Back</i> to change discovery options, or <i>Refresh</i> to search again."))

        self.displayPage(PAGE_DEVICES)


    def loadDevicesTable(self):
        self.DevicesTableWidget.setRowCount(len(self.devices))

        if self.bus == 'net':
            if self.discovery_method == 0:
                headers = [self.__tr('Model'), self.__tr('IP Address'), self.__tr('Host Name'), self.__tr('Device URI')]
                device_uri_col = 3
            else:
                headers = [self.__tr('Model'), self.__tr('Host Name'), self.__tr('Device URI')]
                device_uri_col = 2
        else:
            headers = [self.__tr('Model'), self.__tr('Device URI')]
            device_uri_col = 1

        self.DevicesTableWidget.setColumnCount(len(headers))
        self.DevicesTableWidget.setHorizontalHeaderLabels(headers)
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        for row, d in enumerate(self.devices):
            back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(d)
            model_ui = models.normalizeModelUIName(model)

            i = DeviceTableWidgetItem(QString(model_ui), d)
            i.setFlags(flags)
            self.DevicesTableWidget.setItem(row, 0, i)

            i = QTableWidgetItem(QString(d))
            i.setFlags(flags)
            self.DevicesTableWidget.setItem(row, device_uri_col, i)

            if self.bus == 'net':
                i = QTableWidgetItem(QString(host))
                i.setFlags(flags)
                self.DevicesTableWidget.setItem(row, 1, i)

                if self.discovery_method == 0:
                    i = QTableWidgetItem(QString(self.devices[d][2]))
                    i.setFlags(flags)
                    self.DevicesTableWidget.setItem(row, 2, i)

        self.DevicesTableWidget.resizeColumnsToContents()
        self.DevicesTableWidget.selectRow(0)
        self.DevicesTableWidget.setSortingEnabled(True)
        self.DevicesTableWidget.sortItems(0)


    def clearDevicesTable(self):
        self.DevicesTableWidget.clear()
        self.DevicesTableWidget.setRowCount(0)
        self.DevicesTableWidget.setColumnCount(0)


    def RefreshButton_clicked(self):
        self.clearDevicesTable()
        self.devices = []
        QTimer.singleShot(0, self.showDevicesPage)

    #
    # ADD PRINTER PAGE
    #

    def initAddPrinterPage(self):
        self.mq = {}

        self.connect(self.PrinterNameLineEdit, SIGNAL("textEdited(const QString &)"),
                     self.PrinterNameLineEdit_textEdited)

        self.connect(self.FaxNameLineEdit, SIGNAL("textEdited(const QString &)"),
                     self.FaxNameLineEdit_textEdited)

        self.PrinterNameLineEdit.setValidator(PrinterNameValidator(self.PrinterNameLineEdit))
        self.FaxNameLineEdit.setValidator(PrinterNameValidator(self.FaxNameLineEdit))
        self.FaxNumberLineEdit.setValidator(PhoneNumValidator(self.FaxNumberLineEdit))

        self.OtherPPDButton.setIcon(QIcon(load_pixmap('folder_open', '16x16')))
        self.connect(self.OtherPPDButton, SIGNAL("clicked(bool)"), self.OtherPPDButton_clicked)

        self.OtherPPDButton.setToolTip(self.__tr("Browse for an alternative PPD file for this printer."))

        self.printer_fax_names_same = False
        self.printer_name = ''
        self.fax_name = ''
        self.fax_setup_ok = True
        self.fax_setup = False


    def showAddPrinterPage(self):
        # Install the plugin if needed...
        core = CoreInstall(MODE_CHECK)
        plugin = self.mq.get('plugin', PLUGIN_NONE)
        plugin_reason = self.mq.get('plugin-reason', PLUGIN_REASON_NONE)
        if plugin > PLUGIN_NONE:

            if core.check_for_plugin() != PLUGIN_INSTALLED:
                ok, sudo_ok = pkit.run_plugin_command(plugin == PLUGIN_REQUIRED, plugin_reason)
                if not sudo_ok:
                    FailureUI(self, self.__tr("<b>Unable to find an appropriate su/sudo utiltity to run hp-plugin.</b><p>Install kdesu, gnomesu, or gksu.</p>"))
                    return
                if not ok or core.check_for_plugin() != PLUGIN_INSTALLED:
                    if plugin == PLUGIN_REQUIRED:
                        FailureUI(self, self.__tr("<b>The printer you are trying to setup requires a binary driver plug-in and it failed to install.</b><p>Please check your internet connection and try again.</p><p>Visit <u>http://hplipopensource.com</u> for more infomation.</p>"))
                        return
                    else:
                        WarningUI(self, self.__tr("Either you have chosen to skip the installation of the optional plug-in or that installation has failed.  Your printer may not function at optimal performance."))

        self.setNextButton(BUTTON_ADD_PRINTER)

        if not self.printer_name:
            self.setDefaultPrinterName()

        self.findPrinterPPD()

        if fax_import_ok and prop.fax_build and \
            self.mq.get('fax-type', FAX_TYPE_NONE) not in (FAX_TYPE_NONE, FAX_TYPE_NOT_SUPPORTED):

            self.fax_setup = True
            self.SetupFaxGroupBox.setChecked(True)
            self.SetupFaxGroupBox.setEnabled(True)

            if not self.fax_name:
                self.setDefaultFaxName()

            self.findFaxPPD()

            self.readwriteFaxInformation()

        else:
            self.SetupFaxGroupBox.setChecked(False)
            self.SetupFaxGroupBox.setEnabled(False)
            self.fax_name = ''
            self.fax_name_ok = True
            self.fax_setup = False
            self.fax_setup_ok = True

        self.updatePPD()
        self.setAddPrinterButton()
        self.displayPage(PAGE_ADD_PRINTER)




    def updatePPD(self):
        if self.print_ppd is None:
            log.error("No appropriate print PPD file found for model %s" % self.model)
            self.PPDFileLineEdit.setText(self.__tr('(Not found. Click browse button to select a PPD file.)'))
            try:
                self.PPDFileLineEdit.setStyleSheet("background-color: yellow")
            except AttributeError:
                pass
            self.PrinterDescriptionLineEdit.setText(QString(""))

        else:
            self.PPDFileLineEdit.setText(self.print_ppd[0])
            self.PrinterDescriptionLineEdit.setText(self.print_ppd[1])
            try:
                self.PPDFileLineEdit.setStyleSheet("")
            except AttributeError:
                pass


    def OtherPPDButton_clicked(self, b):
        ppd_file = unicode(QFileDialog.getOpenFileName(self, self.__tr("Select PPD File"),
                                                       sys_conf.get('dirs', 'ppd'),
                                                       self.__tr("PPD Files (*.ppd *.ppd.gz);;All Files (*)")))

        if ppd_file and os.path.exists(ppd_file):
            self.print_ppd = (ppd_file, cups.getPPDDescription(ppd_file))
            self.updatePPD()
            self.setAddPrinterButton()


    def findPrinterPPD(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.print_ppd = None
            self.ppds = cups.getSystemPPDs()
            self.print_ppd = cups.getPPDFile2(self.mq, self.model, self.ppds)
            
        finally:
            QApplication.restoreOverrideCursor()


    def findFaxPPD(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            self.fax_ppd, fax_ppd_name, nick = cups.getFaxPPDFile(self.mq, self.model)
            if self.fax_ppd:
                self.fax_setup_ok = True
            else:
                self.fax_setup_ok = False
                FailureUI(self, self.__tr("<b>Unable to locate the HPLIP Fax PPD file:</b><p>%1.ppd.gz</p><p>Fax setup has been disabled.").arg(fax_ppd_name))
                self.fax_setup = False
                self.SetupFaxGroupBox.setChecked(False)
                self.SetupFaxGroupBox.setEnabled(False)
        finally:
            QApplication.restoreOverrideCursor()


    def setDefaultPrinterName(self):
        self.installed_print_devices = device.getSupportedCUPSDevices(['hp'])
        log.debug(self.installed_print_devices)

        self.installed_queues = [p.name for p in cups.getPrinters()]

        back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(self.device_uri)
        default_model = utils.xstrip(model.replace('series', '').replace('Series', ''), '_')

        printer_name = default_model
        installed_printer_names = device.getSupportedCUPSPrinterNames(['hp'])
        # Check for duplicate names
        if (self.device_uri in self.installed_print_devices and printer_name in self.installed_print_devices[self.device_uri]) \
           or (printer_name in installed_printer_names):
                i = 2
                while True:
                    t = printer_name + "_%d" % i
                    if (t not in installed_printer_names) and (self.device_uri not in self.installed_print_devices or t not in self.installed_print_devices[self.device_uri]):
                        printer_name += "_%d" % i
                        break
                    i += 1

        self.printer_name_ok = True
        self.PrinterNameLineEdit.setText(printer_name)
        log.debug(printer_name)
        self.printer_name = printer_name


    def setDefaultFaxName(self):
        self.installed_fax_devices = device.getSupportedCUPSDevices(['hpfax'])
        log.debug(self.installed_fax_devices)

        self.fax_uri = self.device_uri.replace('hp:', 'hpfax:')

        back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(self.fax_uri)
        default_model = utils.xstrip(model.replace('series', '').replace('Series', ''), '_')

        fax_name = default_model + "_fax"
        installed_fax_names = device.getSupportedCUPSPrinterNames(['hpfax'])
        # Check for duplicate names
        if (self.fax_uri in self.installed_fax_devices and fax_name in self.installed_fax_devices[self.fax_uri]) \
           or (fax_name in installed_fax_names):
                i = 2
                while True:
                    t = fax_name + "_%d" % i
                    if (t not in installed_fax_names) and (self.fax_uri not in self.installed_fax_devices or t not in self.installed_fax_devices[self.fax_uri]):
                        fax_name += "_%d" % i
                        break
                    i += 1

        self.fax_name_ok = True
        self.FaxNameLineEdit.setText(fax_name)
        self.fax_name = fax_name


    def PrinterNameLineEdit_textEdited(self, t):
        self.printer_name = unicode(t)
        self.printer_name_ok = True

        if not self.printer_name:
            self.PrinterNameLineEdit.setToolTip(self.__tr('You must enter a name for the printer.'))
            self.printer_name_ok = False

        elif self.fax_name == self.printer_name:
            s = self.__tr('The printer name and fax name must be different. Please choose different names.')
            self.PrinterNameLineEdit.setToolTip(s)
            self.FaxNameLineEdit.setToolTip(s)
            self.fax_name_ok = False
            self.printer_name_ok = False
            self.printer_fax_names_same = True

        elif self.printer_name in self.installed_queues:
            self.PrinterNameLineEdit.setToolTip(self.__tr('A printer already exists with this name. Please choose a different name.'))
            self.printer_name_ok = False

        elif self.printer_fax_names_same:
            if self.fax_name != self.printer_name:
                self.printer_fax_names_same = False
                self.printer_name_ok = True

                self.FaxNameLineEdit.emit(SIGNAL("textEdited(const QString &)"),
                            self.FaxNameLineEdit.text())

        self.setIndicators()
        self.setAddPrinterButton()


    def FaxNameLineEdit_textEdited(self, t):
        self.fax_name = unicode(t)
        self.fax_name_ok = True

        if not self.fax_name:
            self.FaxNameLineEdit.setToolTip(self.__tr('You must enter a fax name.'))
            self.fax_name_ok = False

        elif self.fax_name == self.printer_name:
            s = self.__tr('The printer name and fax name must be different. Please choose different names.')
            self.PrinterNameLineEdit.setToolTip(s)
            self.FaxNameLineEdit.setToolTip(s)
            self.printer_name_ok = False
            self.fax_name_ok = False
            self.printer_fax_names_same = True

        elif self.fax_name in self.installed_queues:
            self.FaxNameLineEdit.setToolTip(self.__tr('A fax already exists with this name. Please choose a different name.'))
            self.fax_name_ok = False

        elif self.printer_fax_names_same:
            if self.fax_name != self.printer_name:
                self.printer_fax_names_same = False
                self.fax_name_ok = True

                self.PrinterNameLineEdit.emit(SIGNAL("textEdited(const QString&)"),
                            self.PrinterNameLineEdit.text())

        self.setIndicators()
        self.setAddPrinterButton()


    def setIndicators(self):
        if self.printer_name_ok:
            self.PrinterNameLineEdit.setToolTip(QString(""))
            try:
                self.PrinterNameLineEdit.setStyleSheet("")
            except AttributeError:
                pass
        else:
            try:
                self.PrinterNameLineEdit.setStyleSheet("background-color: yellow")
            except AttributeError:
                pass

        if self.fax_name_ok:
            self.FaxNameLineEdit.setToolTip(QString(""))
            try:
                self.PrinterNameLineEdit.setStyleSheet("")
            except AttributeError:
                pass
        else:
            try:
                self.PrinterNameLineEdit.setStyleSheet("background-color: yellow")
            except AttributeError:
                pass


    def setAddPrinterButton(self):
        self.NextButton.setEnabled((self.printer_name_ok and self.print_ppd is not None) and
                                   ((self.fax_setup and self.fax_name_ok) or not self.fax_setup))


    #
    # ADD PRINTER
    #

    def addPrinter(self):
        self.setupPrinter()

        if self.fax_setup:
            self.setupFax()
            self.readwriteFaxInformation(False)

        if self.print_test_page:
            self.printTestPage()

        self.close()



    #
    # SETUP PRINTER/FAX
    #

    def setupPrinter(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            cups.setPasswordPrompt("You do not have permission to add a printer.")
            if not os.path.exists(self.print_ppd[0]): # assume foomatic: or some such
                status, status_str = cups.addPrinter(self.printer_name.encode('utf8'), self.device_uri,
                    self.print_location, '', self.print_ppd[0], self.print_desc)
            else:
                status, status_str = cups.addPrinter(self.printer_name.encode('utf8'), self.device_uri,
                    self.print_location, self.print_ppd[0], '', self.print_desc)

            log.debug("addPrinter() returned (%d, %s)" % (status, status_str))
            self.installed_print_devices = device.getSupportedCUPSDevices(['hp'])

            log.debug(self.installed_print_devices)

            if self.device_uri not in self.installed_print_devices or \
                self.printer_name not in self.installed_print_devices[self.device_uri]:

                QApplication.restoreOverrideCursor()
                if os.geteuid!=0 and utils.addgroup()!=[]:
                    FailureUI(self, self.__tr("<b>Printer queue setup failed. Could not connect to CUPS Server</b><p>Is user added to %s group(s)" %utils.list_to_string(utils.addgroup())))
            else:
                # sending Event to add this device in hp-systray
                utils.sendEvent(EVENT_CUPS_QUEUES_CHANGED,self.device_uri, self.printer_name)

        finally:
            QApplication.restoreOverrideCursor()


    def setupFax(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            cups.setPasswordPrompt("You do not have permission to add a fax device.")
            if not os.path.exists(self.fax_ppd):
                status, status_str = cups.addPrinter(self.fax_name.encode('utf8'),
                    self.fax_uri, self.fax_location, '', self.fax_ppd,  self.fax_desc)
            else:
                status, status_str = cups.addPrinter(self.fax_name.encode('utf8'),
                    self.fax_uri, self.fax_location, self.fax_ppd, '', self.fax_desc)

            log.debug("addPrinter() returned (%d, %s)" % (status, status_str))
            self.installed_fax_devices = device.getSupportedCUPSDevices(['hpfax'])

            log.debug(self.installed_fax_devices)

            if self.fax_uri not in self.installed_fax_devices or \
                self.fax_name not in self.installed_fax_devices[self.fax_uri]:

                QApplication.restoreOverrideCursor()
                FailureUI(self, self.__tr("<b>Fax queue setup failed.</b><p>Please restart CUPS and try again."))
            else:
                 # sending Event to add this device in hp-systray
                utils.sendEvent(EVENT_CUPS_QUEUES_CHANGED,self.fax_uri, self.fax_name)
                
        finally:
            QApplication.restoreOverrideCursor()


    def readwriteFaxInformation(self, read=True):
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

            d = fax.getFaxDevice(self.fax_uri, disable_dbus=True)

            while True:
                try:
                    d.open()
                except Error:
                    error_text = self.__tr("Unable to communicate with the device. Please check the device and try again.")
                    log.error(unicode(error_text))
                    if QMessageBox.critical(self,
                                           self.windowTitle(),
                                           error_text,
                                           QMessageBox.Retry | QMessageBox.Default,
                                           QMessageBox.Cancel | QMessageBox.Escape,
                                           QMessageBox.NoButton) == QMessageBox.Cancel:
                        break

                else:
                    try:
                        tries = 0
                        ok = True

                        while True:
                            tries += 1

                            try:
                                if read:
                                    self.fax_number = unicode(d.getPhoneNum())
                                    self.fax_name_company = unicode(d.getStationName())
                                else:
                                    d.setStationName(self.fax_name_company)
                                    d.setPhoneNum(self.fax_number)

                            except Error:
                                error_text = self.__tr("<b>Device I/O Error</b><p>Could not communicate with device. Device may be busy.")
                                log.error(unicode(error_text))

                                if QMessageBox.critical(self,
                                                       self.windowTitle(),
                                                       error_text,
                                                       QMessageBox.Retry | QMessageBox.Default,
                                                       QMessageBox.Cancel | QMessageBox.Escape,
                                                       QMessageBox.NoButton) == QMessageBox.Cancel:
                                    break


                                time.sleep(5)
                                ok = False

                                if tries > 12:
                                    break

                            else:
                                ok = True
                                break

                    finally:
                        d.close()

                    if ok and read:
                        self.FaxNumberLineEdit.setText(self.fax_number)
                        self.NameCompanyLineEdit.setText(self.fax_name_company)

                    break

        finally:
            QApplication.restoreOverrideCursor()


    def printTestPage(self):
        try:
            d = device.Device(self.device_uri)
        except Error, e:
            FailureUI(self, self.__tr("<b>Device error:</b><p>%s (%s)." % (e.msg, e.opt)))

        else:
            try:
                d.open()
            except Error:
                FailureUI(self, self.__tr("<b>Unable to print to printer.</b><p>Please check device and try again."))
            else:
                if d.isIdleAndNoError():
                    d.close()

                    try:
                        d.printTestPage(self.printer_name)
                    except Error, e:
                        if e.opt == ERROR_NO_CUPS_QUEUE_FOUND_FOR_DEVICE:
                            FailureUI(self, self.__tr("<b>No CUPS queue found for device.</b><p>Please install the printer in CUPS and try again."))
                        else:
                            FailureUI(self, self.__tr("<b>Printer Error</b><p>An error occured: %s (code=%d)." % (e.msg, e.opt)))
                else:
                    FailureUI(self, self.__tr("<b>Printer Error.</b><p>Printer is busy, offline, or in an error state. Please check the device and try again."))
                    d.close()

    #
    # Remove Page
    #

    def initRemovePage(self):
        pass


    def showRemovePage(self):
        self.displayPage(PAGE_REMOVE)
        self.StepText.setText(self.__tr("Step 1 of 1"))
        self.setNextButton(BUTTON_REMOVE)
        self.BackButton.setEnabled(False)
        self.NextButton.setEnabled(False)

        self.RemoveDevicesTableWidget.verticalHeader().hide()

        self.installed_printers = device.getSupportedCUPSPrinters(['hp', 'hpfax'])
        log.debug(self.installed_printers)

        if not self.installed_printers:
            FailureUI(self, self.__tr("<b>No printers or faxes found to remove.</b><p>You must setup a least one printer or fax before you can remove it."))
            self.close()
            return

        self.RemoveDevicesTableWidget.setRowCount(len(self.installed_printers))

        headers = [self.__tr("Select"), self.__tr('Printer (Queue) Name'), self.__tr('Type'), self.__tr('Device URI')]

        self.RemoveDevicesTableWidget.setColumnCount(len(headers))
        self.RemoveDevicesTableWidget.setHorizontalHeaderLabels(headers)
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled

        row = 0
        for p in self.installed_printers:
            widget = QCheckBox(self.RemoveDevicesTableWidget)
            self.connect(widget, SIGNAL("stateChanged(int)"), self.CheckBox_stateChanged)
            self.RemoveDevicesTableWidget.setCellWidget(row, 0, widget)

            back_end, is_hp, bus, model, serial, dev_file, host, zc, port = \
                device.parseDeviceURI(p.device_uri)

            if self.device_uri is not None and self.device_uri == p.device_uri:
                widget.setCheckState(Qt.Checked)

            i = QTableWidgetItem(QString(p.name))
            i.setFlags(flags)
            i.setData(Qt.UserRole, QVariant(p.name))
            self.RemoveDevicesTableWidget.setItem(row, 1, i)

            if back_end == 'hpfax':
                typ = self.__tr("Fax")
            else:
                typ = self.__tr("Printer")

            i = QTableWidgetItem(typ)
            i.setFlags(flags)
            self.RemoveDevicesTableWidget.setItem(row, 2, i)

            i = QTableWidgetItem(QString(p.device_uri))
            i.setFlags(flags)
            self.RemoveDevicesTableWidget.setItem(row, 3, i)

            row += 1

        self.RemoveDevicesTableWidget.resizeColumnsToContents()


    def CheckBox_stateChanged(self, i):
        for row in xrange(self.RemoveDevicesTableWidget.rowCount()):
            widget = self.RemoveDevicesTableWidget.cellWidget(row, 0)
            if widget.checkState() == Qt.Checked:
                self.NextButton.setEnabled(True)
                break
        else:
            self.NextButton.setEnabled(False)


    #
    # Misc
    #

    def NextButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_DISCOVERY:
            self.manual = self.ManualGroupBox.isChecked()
            self.param = unicode(self.ManualParamLineEdit.text())
            self.jd_port = self.JetDirectSpinBox.value()
            self.search = unicode(self.SearchLineEdit.text())
            self.device_desc = int(self.DeviceTypeComboBox.itemData(self.DeviceTypeComboBox.currentIndex()).toInt()[0])
            self.discovery_method = self.NetworkDiscoveryMethodComboBox.currentIndex()

            if self.WirelessButton.isChecked():
                dlg = WifiSetupDialog(self, device_uri=None, standalone=False)
                dlg.exec_()

                if dlg.success == SUCCESS_CONNECTED:
                    self.manual = True
                    self.param = dlg.hn
                    self.bus = 'net'
            if not self.WirelessButton.isChecked():
                self.showDevicesPage()
           
        elif p == PAGE_DEVICES:
            row = self.DevicesTableWidget.currentRow()
            self.device_uri = self.DevicesTableWidget.item(row, 0).device_uri
            self.mq = device.queryModelByURI(self.device_uri)
            back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(self.device_uri)
            self.model = models.normalizeModelName(model).lower()
            self.showAddPrinterPage()

        elif p == PAGE_ADD_PRINTER:
            self.print_test_page = self.SendTestPageCheckBox.isChecked()
            self.print_desc = unicode(self.PrinterDescriptionLineEdit.text()).encode('utf8')
            self.print_location = unicode(self.PrinterLocationLineEdit.text()).encode('utf8')
            self.fax_setup = self.SetupFaxGroupBox.isChecked()
            self.fax_desc = unicode(self.FaxDescriptionLineEdit.text()).encode('utf8')
            self.fax_location = unicode(self.FaxLocationLineEdit.text()).encode('utf8')
            self.fax_name_company = unicode(self.NameCompanyLineEdit.text()).encode('utf8')
            self.fax_number = unicode(self.FaxNumberLineEdit.text()).encode('utf8')
            self.addPrinter()

        elif p == PAGE_REMOVE:
            for row in xrange(self.RemoveDevicesTableWidget.rowCount()):
                widget = self.RemoveDevicesTableWidget.cellWidget(row, 0)
                if widget.checkState() == Qt.Checked:
                    item = self.RemoveDevicesTableWidget.item(row, 1)
                    printer = unicode(item.data(Qt.UserRole).toString()).encode('utf-8')
                    log.debug("Removing printer: %s" % printer)
                    if cups.delPrinter(printer) == 0 and os.geteuid!=0 and utils.addgroup()!=[]:
                            FailureUI(self, self.__tr("<b>Unable to delete printer queue. Could not connect to CUPS Server</b><p>Is user added to %s group(s)" %utils.list_to_string(utils.addgroup())))
            self.close()

        else:
            log.error("Invalid page!") # shouldn't happen!


    def BackButton_clicked(self):
        p = self.StackedWidget.currentIndex()
        if p == PAGE_DEVICES:
            self.devices = {}
            self.showDiscoveryPage()

        elif p == PAGE_ADD_PRINTER:
            self.showDevicesPage()

        else:
            log.error("Invalid page!") # shouldn't happen!


    def CancelButton_clicked(self):
        self.close()


    def displayPage(self, page):
        self.StackedWidget.setCurrentIndex(page)
        self.updateStepText(page)


    def setNextButton(self, typ=BUTTON_FINISH):
        if typ == BUTTON_ADD_PRINTER:
            self.NextButton.setText(self.__tr("Add Printer"))
        elif typ == BUTTON_NEXT:
            self.NextButton.setText(self.__tr("Next >"))
        elif typ == BUTTON_FINISH:
            self.NextButton.setText(self.__tr("Finish"))
        elif typ == BUTTON_REMOVE:
            self.NextButton.setText(self.__tr("Remove"))


    def updateStepText(self, p):
        self.StepText.setText(self.__tr("Step %1 of %2").arg(p+1).arg(self.max_page+1))


    def __tr(self,s,c = None):
        return qApp.translate("SetupDialog",s,c)


