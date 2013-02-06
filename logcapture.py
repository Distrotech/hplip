#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) Copyright 2003-2014 Hewlett-Packard Development Company, L.P.
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
__title__ = 'HPLIP logs capture Utility'
__mod__ = 'hp-logcapture'
__doc__ = """Captures the HPLIP log files."""

import os
import sys
import getopt
import glob

from base.g import *
from base import utils,tui,module


CUPS_FILE='/etc/cups/cupsd.conf'
CUPS_BACKUP_FILE='/etc/cups/cupsd.conf_orginal'
LOG_FOLDER_PATH='./'
LOG_FOLDER_NAME='hplip_troubleshoot_logs'
LOG_FILES=LOG_FOLDER_PATH + LOG_FOLDER_NAME
TMP_DIR='/var/log/hp/tmp'
############ enable_log() function ############
#This function changes CUPS conf log level to debug and restarts CUPS service.

def enable_log():
    result = False
    cmd='cp -f %s %s'%(CUPS_FILE,CUPS_BACKUP_FILE)
    log.debug("Backup CUPS conf file. cmd =%s"%cmd)
    sts,out=utils.run(cmd)
    if sts != 0:
        log.error("Failed to take back cups file=%s"%CUPS_FILE)

    #check if cups is log level enabled or disable
    cmd="grep 'LogLevel warn' %s"%CUPS_FILE
    log.debug ("cmd= %s"%cmd)
    sts,out=utils.run(cmd)
    if sts == 0:
        cmd = "vi -c '%s/LogLevel warn/LogLevel debug\rhpLogLevel 15/' -c 'wq' %s"%("%s",CUPS_FILE)
        log.debug("Changing 'Log level' to debug. cmd=%s"%cmd)
        sts, cmd = utils.run(cmd)
        if sts != 0:
           log.error("Failed to update Loglevel to Debug in cups=%s"%CUPS_FILE)

        cmd=None
        path=utils.which('service')
        if path:
           cmd = os.path.join(path, 'service')+" cups restart"
        elif os.path.exists('/etc/init.d/cups'):
           cmd = "/etc/init.d/cups restart"
        else:
           log.error("service command not found.. Please restart cups manually..")
        
        if cmd:
           log.debug("CUPS restart cmd = %s"%cmd)
           sts,out = utils.run(cmd)
           if sts == 0:
               result = True

    return result

############ restore_loglevels() function ############
#This function restores CUPS conf file to previous value and restarts CUPS service.

def restore_loglevels():
    cmd='cp -f %s %s'%(CUPS_BACKUP_FILE,CUPS_FILE)
    log.debug("Restoring CUPS conf file. cmd=%s"%cmd)
    sts, out = utils.run(cmd)
    if sts == 0:
       cmd='rm -f %s'%CUPS_BACKUP_FILE
       log.debug("Removing Temporary file.. cmd=%s"%cmd)
       sts,out = utils.run(cmd)
       if sts != 0:
            log.warn("Failed to remove the Temporary backup file=%s"%CUPS_BACKUP_FILE)
    else:
       log.error("Failed to restore cups config file = %s"%CUPS_FILE)
    log.debug("Restarting CUPS service")
    cmd=None
    path=utils.which('service')
    if path:
        cmd = os.path.join(path, 'service')+" cups restart"
    elif os.path.exists('/etc/init.d/cups'):
        cmd = "/etc/init.d/cups restart"
    else:
        log.error("service command not found.. Please restart cups manually..")

    if cmd:
        log.debug("CUPS restart cmd = %s"%cmd)
        sts,out = utils.run(cmd)
        if sts == 0:
           result = True

    return result

def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, __mod__, __version__)
    sys.exit(0)


def backup_clearLog(strLog):
    if os.path.exists(strLog):
        iArch =1
        while os.path.exists("%s.%d"%(strLog, iArch)) or os.path.exists("%s.%d.gz"%(strLog, iArch)):
            iArch +=1
        sts,out = utils.run('cp %s %s.%d'%(strLog, strLog, iArch))
        if sts != 0:
            log.error("Failed to archive %s log file"%strLog)
        else:
#            sts,out = utils.run('cp /dev/null %s'%strLog)
            sts = os.system('cat /dev/null > %s'%strLog)
            if sts != 0:
                log.warn("Failed to clear the %s log file"%strLog)
            if utils.which('gzip'):
                sts,out = utils.run ('gzip %s.%d'%(strLog, iArch))
                if sts != 0:
                    log.info("Existing %s log file copied to %s.%d"%(strLog, strLog, iArch))
                else:
                    log.info("Existing %s log file copied to %s.%d.gz"%(strLog, strLog, iArch))
            else:
                log.info("Existing %s log file copied to %s.%d"%(strLog, strLog, iArch))
         


USAGE = [(__doc__, "", "name", True),
         ("Usage: [su -c /sudo] %s [OPTIONS]" % __mod__, "", "summary", True),
         ("e.g. su -c '%s'"%__mod__,"","summary",True),
         utils.USAGE_OPTIONS,
         utils.USAGE_HELP,
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
        ]


######## Main #######
try:
    mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE,
                    (INTERACTIVE_MODE, GUI_MODE),
                    (UI_TOOLKIT_QT3, UI_TOOLKIT_QT4), True, True)

    opts, device_uri, printer_name, mode, ui_toolkit, loc = \
               mod.parseStdOpts('hl:g', ['help', 'help-rest', 'help-man', 'help-desc', 'logging=', 'debug'],handle_device_printer=False)
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

    elif o == '--help-desc':
        print __doc__,
        clean_exit(0,False)

    elif o in ('-l', '--logging'):
        log_level = a.lower().strip()
        if not log.set_level(log_level):
            usage()

    elif o in ('-g', '--debug'):
        log.set_level('debug')


if os.getuid() != 0:
    log.error("logCapture needs root permissions since cups service restart requires....")
    sys.exit()

cmd = "mkdir -p %s"%LOG_FILES
log.debug("Creating temporary logs folder =%s"%cmd)
sts, out = utils.run(cmd)
if sts != 0:
   log.error("Failed to create directory =%s. Exiting"%LOG_FILES)
   sys.exit(1)


enable_log()

#### Clearing previous logs.. ###########
ok,user_input = tui.enter_choice("Archiving system logs (i.e. syslog, message, error_log). Press (y=yes*, n=no, q=quit):",['y', 'n','q'], 'y')
if not ok or user_input == "q":
    restore_loglevels()
    log.warn("User exit")
    sys.exit(1)

if ok and user_input == "y":
    backup_clearLog('/var/log/syslog')
    backup_clearLog('/var/log/messages')
    backup_clearLog('/var/log/cups/error_log')

File_list, File_list_str =utils.expand_list('%s/*.bmp'%TMP_DIR)
if File_list:
    cmd= 'rm -rf %s'%File_list_str
    log.debug("cmd= %s"%cmd)
    sts,out = utils.run(cmd)
    if sts != 0:
        log.warn("Failed to remove %s files"%File_list_st)

File_list, File_list_str =utils.expand_list('%s/*.out'%TMP_DIR)
if File_list:
    cmd= 'rm -rf %s'%File_list_str
    log.debug("cmd= %s"%cmd)
    sts,out = utils.run(cmd)
    if sts != 0:
        log.warn("Failed to remove %s files"%File_list_st)


######## Waiting for user to completed job #######
while 1:
    log.info(log.bold("\nPlease perform the tasks (Print, scan, fax) for which you need to collect the logs."))
    ok,user_input =tui.enter_choice("Are you done with taks?. Press (y=yes*, q=quit):",['y','q'], 'y')
    if ok and user_input == "y":
        break;
    elif not ok or user_input == "q":
        restore_loglevels()
        log.warn("User exit")
        sys.exit(1)
   
######## Copying logs to Temporary log folder #######
sts,out = utils.run('hp-check')
if sts != 0:
    log.error("Failed to run hp-check command")

log.debug("Copying logs to Temporary folder =%s"%LOG_FILES)
if os.path.exists('/var/log/syslog'):
    sts,out = utils.run ('cp -f /var/log/syslog %s/syslog.log'%LOG_FILES)
    if sts != 0:
      log.error("Failed to capture %s log file."%("/var/log/syslog"))

if os.path.exists('/var/log/messages'):
    sts,out = utils.run('cp -f /var/log/messages %s/messages.log'%LOG_FILES)
    if sts != 0:
      log.error("Failed to capture %s log file."%("/var/log/messages"))


if os.path.exists('/var/log/cups/error_log'):
    sts,out = utils.run('cp -f /var/log/cups/error_log %s/cups_error_log.log'%LOG_FILES)
    if sts != 0:
      log.error("Failed to capture %s log file."%("/var/log/cups/error_log"))


File_list, File_list_str = utils.expand_list('/var/log/hp/*.log')
if File_list:
    sts,out = utils.run('cp -f %s %s'%(File_list_str, LOG_FILES))
    if sts != 0:
      log.error("Failed to capture %s log files."%(File_list_str))

File_list, File_list_str =utils.expand_list('%s/*.bmp'%TMP_DIR)
if File_list:
    sts,out = utils.run('cp -f %s %s'%(File_list_str, LOG_FILES))
    if sts != 0:
      log.error("Failed to capture %s log files."%(File_list_str))


File_list, File_list_str =utils.expand_list('%s/*.out'%TMP_DIR)
if File_list:
    sts,out = utils.run('cp -f %s %s'%(File_list_str, LOG_FILES))
    if sts != 0:
      log.error("Failed to capture %s log files."%(File_list_str))


sts,out = utils.run('mv -f ./hp-check.log %s'%LOG_FILES)
if sts != 0:
    log.error("Failed to capture %s log files."%("./hp-check.log"))
ists,out = utils.run('chmod 666 -R %s'%LOG_FILES)
if sts != 0:
    log.error("Failed to change permissions for %s. Only root can access."%(LOG_FILES))

######## Compressing log files #######
cmd = 'tar -zcf %s.tar.gz %s'%(LOG_FOLDER_NAME,LOG_FILES)
log.debug("Compressing logs. cmd =%s"%cmd)

sts_compress,out = utils.run(cmd)
if sts != 0:
    log.error("Failed to compress %s folder."%(LOG_FILES))
else:
    log.debug("Changing Permissions of ./%s.tar.gz "%LOG_FOLDER_NAME)
    sts,out = utils.run('chmod 666 -R ./%s.tar.gz'%(LOG_FOLDER_NAME))
    if sts != 0:
        log.error("Failed to change permissions for %s.tar.gz Only root can access."%(LOG_FILES))
    log.debug("Removing Temporary log files..")
    sts,out = utils.run('rm -rf %s'%LOG_FILES)
    if sts != 0:
        log.error("Failed to remove temporary files. Remove manually."%(LOG_FILES))

restore_loglevels()

log.info("")
log.info("")
if sts_compress == 0:
    log.info(log.bold("Logs are saved as %s/%s.tar.gz"%( os.getcwd(),LOG_FOLDER_NAME)))
else:
    log.info(log.bold("Logs are saved as %s/%s"%(os.getcwd(),LOG_FOLDER_NAME)))
log.info("")
