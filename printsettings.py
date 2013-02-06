#!/usr/bin/env python
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

__version__ = '1.0'
__title__ = 'Printer Settings Utility'
__mod__ = 'hp-printsettings'
__doc__ = "Printer settings (options) utility for HPLIP supported printers."

#Std Lib
import sys
import re
import getopt
import time
import operator
import os

# Local
from base.g import *
from base import device, utils, maint, tui, module
from prnt import cups


try:
    mod = module.Module(__mod__, __title__, __version__, __doc__, None,
                        (GUI_MODE,), (UI_TOOLKIT_QT4,))

    mod.setUsage(module.USAGE_FLAG_DEVICE_ARGS,
             see_also_list=['hp-toolbox', 'hp-print'])

    opts, device_uri, printer_name, mode, ui_toolkit, loc = \
        mod.parseStdOpts('', ['fax'])

    fax_mode = False
    for o, a in opts:
        if o == '--fax':
            fax_mode = True

    if fax_mode:
        back_end_filter = ['hpfax']
    else:
        back_end_filter = ['hp', 'hpfax']

    printer_name, device_uri = mod.getPrinterName(printer_name, device_uri, back_end_filter)

    if ui_toolkit == 'qt3':
        log.error("%s requires Qt4 support. Use hp-toolbox to adjust print settings. Exiting." % __mod__)
        sys.exit(1)

    if not utils.canEnterGUIMode4():
        log.error("%s requires Qt4 GUI support. Exiting." % __mod__)
        sys.exit(1)

    try:
        from PyQt4.QtGui import QApplication
        from ui4.printsettingsdialog import PrintSettingsDialog
    except ImportError:
        log.error("Unable to load Qt4 support. Is it installed?")
        sys.exit(1)

    app = QApplication(sys.argv)

    dialog = PrintSettingsDialog(None, printer_name, fax_mode)
    dialog.show()
    try:
        log.debug("Starting GUI loop...")
        app.exec_()
    except KeyboardInterrupt:
        log.error("User exit")
        sys.exit(0)

except KeyboardInterrupt:
    log.error("User exit")

log.info("")
log.info("Done.")

