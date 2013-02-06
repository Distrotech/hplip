#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2011 Hewlett-Packard Development Company, L.P.
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
# Author: Amarnath Chitumalla, Suma Byrappa
#

__version__ = '1.0'
__mod__ = 'hp-diagnose_plugin'
__title__ = 'Plugin Download and Install Utility'
__doc__ = ""

# Std Lib
import sys
import getopt
import time
import os.path
import re
import os

# Local
from base.g import *
from base import utils, module

USAGE = [ (__doc__, "", "name", True),
          ("Usage: %s [OPTIONS]" % __mod__, "", "summary", True),
          utils.USAGE_OPTIONS,
          utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
          utils.USAGE_HELP,
          utils.USAGE_SPACE,
          utils.USAGE_SEEALSO,
          ("hp-plugin", "", "seealso", False),
          ("hp-setup", "", "seealso", False),
          ("hp-firmware", "", "seealso", False),
        ]


mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE,
                    (INTERACTIVE_MODE, GUI_MODE),
                    (UI_TOOLKIT_QT3, UI_TOOLKIT_QT4), True)

opts, device_uri, printer_name, mode, ui_toolkit, loc = \
    mod.parseStdOpts( handle_device_printer=False)

plugin_path = None
install_mode = PLUGIN_REQUIRED
plugin_reason = PLUGIN_REASON_NONE

if mode == GUI_MODE:
    if ui_toolkit == 'qt3':
        log.error("Unable to load Qt3. Please use Qt4")

    else: #qt4
        if not utils.canEnterGUIMode4():
            log.error("%s requires GUI support . Is Qt4 installed?" % __mod__)
            sys.exit(1)

        try:
            from PyQt4.QtGui import QApplication, QMessageBox
            from ui4.plugindiagnose import PluginDiagnose
	    from installer import core_install
        except ImportError:
            log.error("Unable to load Qt4 support. Is it installed?")
            sys.exit(1)

        app = QApplication(sys.argv)
        core = core_install.CoreInstall(core_install.MODE_CHECK)
        plugin_sts = core.check_for_plugin()
        if plugin_sts == PLUGIN_INSTALLED:
            log.info("Device Plugin is already installed")
            sys.exit(0)
        elif plugin_sts == PLUGIN_VERSION_MISMATCH:
            dialog = PluginDiagnose(None, install_mode, plugin_reason, True)
        else:
            dialog = PluginDiagnose(None, install_mode, plugin_reason)

        dialog.show()
        try:
            log.debug("Starting GUI loop...")
            app.exec_()
        except KeyboardInterrupt:
            log.error("User exit")
            sys.exit(0)
else: #Interaction mode
    log.error("Only Qt4 GUI mode is supported \n")
    usage()

log.info("")
log.info("Done.")
