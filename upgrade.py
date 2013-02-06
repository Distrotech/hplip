#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2011-2014 Hewlett-Packard Development Company, L.P.
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
# Author: Amarnath Chitumalla
#

__version__ = '1.0'
__title__ = 'HPLIP upgrade latest version'
__mod__ = 'hp-upgrade'
__doc__ = "HPLIP installer to upgrade to latest version."

# Std Lib
import getopt, os, sys, re, time

# Local
from base.g import *
from base import utils, tui, module
from installer.core_install import *



USAGE = [(__doc__, "", "name", True),
         ("Usage: %s [OPTIONS]" % __mod__, "", "summary", True),
         utils.USAGE_SPACE,
         utils.USAGE_MODE,
         ("Run in interactive mode:", "-i or --interactive (Default)", "option", False),
         ("Run in graphical UI mode:", "-u or --gui (future use)", "option", False),
         utils.USAGE_SPACE,
         utils.USAGE_OPTIONS,
         utils.USAGE_HELP,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         ("Check for update and notify:","--notify","option",False),
         ("Check only available version:","--check","option",False),
         ("Non-interactive mode:","-n(Without asking permissions)(future use)","option",False),
         ("Download Path to install from local system:","-p<path>","option", False),
         ("Download HPLIP package location:","-d<path> (default location /tmp/)","option", False),
         ("Override existing HPLIP installation even if latest vesrion is installed:","-o","option",False),
         ("Take options from the file instead of command line:","-f<file> (future use)","option",False)
        ]


def hold_terminal():
    if DONOT_CLOSE_TERMINAL:
        log.info("\n\nPlease close this terminal manually. ")
        while 1:
            pass

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, __mod__, __version__)
    hold_terminal()
    sys.exit(0)

def clean_exit(code=0, waitTerminal=True):
    if not NOTIFY and not CHECKING_ONLY and not IS_QUIET_MODE:
        log.info("Completed..")
    change_spinner_state(True)
    mod.unlockInstance()
    hold_terminal()
    sys.exit(code)


def parse_HPLIP_version(hplip_version_file, pat):
    ver = "0.0.0"
    if not os.path.exists(hplip_version_file):
        return ver

    try:
        fp= file(hplip_version_file, 'r')
    except IOError:
        log.error("Failed to get hplip version since %s file is not found."%hplip_version_file)
        return ver
    data = fp.read()
    for line in data.splitlines():
        if pat.search(line):
            ver = pat.search(line).group(1)
            break
    
    log.debug("Latest HPLIP version = %s." % ver)
    return ver


log.set_module(__mod__)

mode = INTERACTIVE_MODE
auto = False
HPLIP_PATH=None
TEMP_PATH="/tmp/"
FORCE_INSTALL=False
CHECKING_ONLY=False
NOTIFY=False
HPLIP_VERSION_INFO_SITE ="http://hplip.sourceforge.net/hplip_web.conf"
HPLIP_WEB_SITE ="http://hplipopensource.com/hplip-web/index.html"
IS_QUIET_MODE = False
DONOT_CLOSE_TERMINAL = False

try:
    mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE,
                    (INTERACTIVE_MODE, GUI_MODE),
                    (UI_TOOLKIT_QT3, UI_TOOLKIT_QT4), True, True)

    opts, device_uri, printer_name, mode, ui_toolkit, loc = \
               mod.parseStdOpts('hl:gniup:d:of:sw', ['notify','check','help', 'help-rest', 'help-man', 'help-desc', 'interactive', 'gui', 'lang=','logging=', 'debug'],
                     handle_device_printer=False)



    mod.lockInstance('',True)
except getopt.GetoptError, e:
    log.error(e.msg)
    usage()

if os.getenv("HPLIP_DEBUG"):
    log.set_level('debug')

for o, a in opts:
    if o in ('-h', '--help'):
        usage()

    elif o == '--help-rest':
        usage('rest')

    elif o == '--help-man':
        usage('man')

    elif o in ('-q', '--lang'):
        language = a.lower()

    elif o == '--help-desc':
        print __doc__,
        clean_exit(0,False)

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o in ('-g', '--debug'):
        log.set_level('debug')

    elif o == '-n':
        mode = NON_INTERACTIVE_MODE
        log.info("NON_INTERACTIVE mode is not yet supported.")
        usage()
        clean_exit(0,False)
 
    elif o == '-p':
        HPLIP_PATH=a

    elif o == '-d':
        TEMP_PATH=a
    
    elif o == '-o':
        FORCE_INSTALL = True
    
    elif o in ('-u', '--gui'):
        log.info("GUI is not yet supported.")
        usage()
        clean_exit(0, False)
    elif o == '--check':
        CHECKING_ONLY = True
    elif o == '--notify':
        NOTIFY = True
    elif o == '-s':
        IS_QUIET_MODE = True
    elif o == '-f':
        log.info("Option from file is not yet supported")
        usage()
        clean_exit(0, False)
    elif o == '-w':
        DONOT_CLOSE_TERMINAL = True

if not NOTIFY and not CHECKING_ONLY and not IS_QUIET_MODE:
    mod.quiet= False
    mod.showTitle()

log_file = os.path.normpath('/var/log/hp/hp-upgrade.log')

if os.path.exists(log_file):
    os.remove(log_file)

log.set_logfile(log_file)
log.set_where(log.LOG_TO_CONSOLE_AND_FILE)


log.debug("Upgrade log saved in: %s" % log.bold(log_file))
log.debug("")
try:
    change_spinner_state(False)
    core =  CoreInstall(MODE_CHECK)
#    core.init()
    if not core.check_network_connection():
        log.error("Either Internet is not working or Wget is not installed.")
        clean_exit(0)

    installed_version=sys_conf.get("hplip","version","0.0.0")
    log.debug("HPLIP previous installed version =%s." %installed_version)



    HPLIP_latest_ver="0.0.0"
    # get HPLIP version info from hplip_web.conf file
    sts, HPLIP_Ver_file = utils.download_from_network(HPLIP_VERSION_INFO_SITE)    
    if sts is True:
        hplip_version_conf = ConfigBase(HPLIP_Ver_file)
        HPLIP_latest_ver = hplip_version_conf.get("HPLIP","Latest_version","0.0.0")

    # get HPLIP version info from hplip site
    if HPLIP_latest_ver == "0.0.0":	## if failed to connect the sourceforge site, then check HPLIP site.
        pat = re.compile(r"""The current version of the HPLIP solution is version (\d{1,}\.\d{1,}\.\d{1,}[a-z]{0,})\. \(.*""")
        sts, HPLIP_Ver_file = utils.download_from_network(HPLIP_WEB_SITE)
        if sts is True:
            HPLIP_latest_ver = parse_HPLIP_version(HPLIP_Ver_file, pat)

    if HPLIP_latest_ver == "0.0.0":
        log.error("Failed to get latest version of HPLIP.")
        clean_exit(0)

            
    if CHECKING_ONLY is True:
        user_conf.set('upgrade','latest_available_version',HPLIP_latest_ver)
        log.debug("Available HPLIP version =%s."%HPLIP_latest_ver)
    elif NOTIFY is True:
        user_conf.set('upgrade','latest_available_version',HPLIP_latest_ver)
        if not utils.Is_HPLIP_older_version(installed_version, HPLIP_latest_ver):
            log.debug("Latest version of HPLIP is already installed.")
        else:
                  
            msg = "Latest version of HPLIP-%s is available."%HPLIP_latest_ver
            if core.is_auto_installer_support():
                distro_type= 1
            else:
                distro_type= 2


            if ui_toolkit == 'qt3':
                if not utils.canEnterGUIMode():
                    log.error("%s requires GUI support. Is Qt3 Installed?.. Exiting." % __mod__)
                    clean_exit(1)

                try:
                    from qt import *
                    from ui.upgradeform import UpgradeForm
                except ImportError:
                    log.error("Unable to load Qt3 support. Is it installed? ")
                    clean_exit(1)
                    

                # create the main application object
                app = QApplication(sys.argv)
                QObject.connect(app, SIGNAL("lastWindowClosed()"), app, SLOT("quit()"))
                dialog = UpgradeForm(None, "",0,0,distro_type, msg)
                dialog.show()

                log.debug("Starting GUI loop...")
                app.exec_loop()
                    

            else: #qt4
                if not utils.canEnterGUIMode4():
                    log.error("%s requires GUI support . Is Qt4 installed?.. Exiting." % __mod__)
                    clean_exit(1)

                try:
                    from PyQt4.QtGui import QApplication, QMessageBox
                    from ui4.upgradedialog import UpgradeDialog
                except ImportError:
                    log.error("Unable to load Qt4 support. Is it installed?")
                    clean_exit(1)

                app = QApplication(sys.argv)
                dialog = UpgradeDialog(None, distro_type, msg)
            
            
                dialog.show()
                log.debug("Starting GUI loop...")
                app.exec_()
                    
    else:
        if FORCE_INSTALL is False:
            if utils.Is_HPLIP_older_version(installed_version, HPLIP_latest_ver):
                if IS_QUIET_MODE:
                    log.info("Newer version of HPLIP-%s is available."%HPLIP_latest_ver)
                ok,choice = tui.enter_choice("Press 'y' to continue to upgrade HPLIP-%s (y=yes*, n=no):"%HPLIP_latest_ver, ['y','n'],'y')
                if not ok or choice == 'n':
                    log.info("Recommended to install latesr version of HPLIP-%s"%HPLIP_latest_ver)
                    clean_exit(0, False)
            else:
                log.info("Latest version of HPLIP is already installed.")
                clean_exit(0,False)
    
        # check distro information.
        if not core.is_auto_installer_support():
            log.info("Please install HPLIP manually as mentioned in 'http://hplipopensource.com/hplip-web/install/manual/index.html' site")
            clean_exit(0)
 
        # check systray is running?
        status,output = utils.Is_Process_Running('hp-systray')
        if status is True:
            ok,choice = tui.enter_choice("\nSome HPLIP applications are running. Press 'y' to close applications or press 'n' to quit upgrade(y=yes*, n=no):",['y','n'],'y')
            if not ok or choice =='n':
                log.info("Manually close HPLIP applications and run hp-upgrade again.")
                clean_exit(0, False)
        
            try:
            # dBus
            #import dbus
                from dbus import SystemBus, lowlevel
            except ImportError:
                log.error("Unable to load DBus.")
                pass
            else:
                try:
                    args = ['', '', EVENT_SYSTEMTRAY_EXIT, prop.username, 0, '', '']
                    msg = lowlevel.SignalMessage('/', 'com.hplip.StatusService', 'Event')
                    msg.append(signature='ssisiss', *args)
                    log.debug("Sending close message to hp-systray ...")
                    SystemBus().send_message(msg)
                    time.sleep(0.5)
                except:
                    log.error("Failed to send DBus message to hp-systray/hp-toolbox.")
                    pass

    
        toolbox_status,output = utils.Is_Process_Running('hp-toolbox')
#        systray_status,output = utils.Is_Process_Running('hp-systray')
        if toolbox_status is True:
            log.error("Failed to close either HP-Toolbox/HP-Systray. Manually close and run hp-upgrade again.")
            clean_exit(0)

      
        if HPLIP_PATH is not None:
            if os.path.exists(HPLIP_PATH):
                download_file = HPLIP_PATH
            else:
                log.error("%s file is not present. Downloading from Net..." %HPLIP_PATH)
                HPLIP_PATH = None
    
        if HPLIP_PATH is None:
            url="http://sourceforge.net/projects/hplip/files/hplip/%s/hplip-%s.run/download" %(HPLIP_latest_ver, HPLIP_latest_ver)
            download_file = None
            if TEMP_PATH:
                download_file = "%s/hplip-%s.run" %(TEMP_PATH,HPLIP_latest_ver)
            log.info("Downloading hplip-%s.run file..... Please wait. "%HPLIP_latest_ver ) 
            sts,download_file = utils.download_from_network(url, download_file, True)

            if not os.path.exists(download_file):
                log.error("Failed to download %s file."%download_file)
                clean_exit()
    
        # Installing hplip run.
        cmd = "sh %s" %(download_file)
        log.debug("Upgrading  %s and cmd =%s " %(download_file, cmd))
        os.system(cmd)
    if not NOTIFY and not CHECKING_ONLY:
        log.info(log.bold("Upgrade is Completed"))
    change_spinner_state(True)
    mod.unlockInstance()
    hold_terminal()

#    log.info("HPLIP upgrade is completed")
except KeyboardInterrupt:
    change_spinner_state(True)
    mod.unlockInstance()
    log.error("User exit")
    hold_terminal()

