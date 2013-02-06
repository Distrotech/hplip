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
__title__ = 'HP device setup using USB'
__mod__ = 'hp-config_usb_printer'
__doc__ = "Detects HP printers connected using USB and installs HPLIP printers and faxes in the CUPS spooler. Tries to automatically determine the correct PPD file to use."

# Std Lib
import sys
import os
import getopt
import commands
import re
import time

# Local
from base.g import *
from base import device,utils, tui, models,module
from prnt import cups


LPSTAT_PAT = re.compile(r"""(\S*): (.*)""", re.IGNORECASE)
USB_PATTERN = re.compile(r'''serial=(.*)''',re.IGNORECASE)
BACK_END_PATTERN = re.compile(r'''(.*):(.*)''',re.IGNORECASE)
DBUS_SERVICE='com.hplip.StatusService'

##### METHODS #####

# Returns already existing print queues for this printer.
def get_already_added_queues(udev_MDL, udev_serial_no, udev_back_end,remove_non_hp_config):
    status, output = utils.run('lpstat -v')

    same_printer_queues = []
    for p in output.splitlines():
        try:
            match = LPSTAT_PAT.search(p)
            printer_name = match.group(1)
            device_uri = match.group(2)
            if device_uri.startswith("cups-pdf:/"):
                  continue
            if not USB_PATTERN.search(device_uri):
                  continue

            back_end = BACK_END_PATTERN.search(device_uri).group(1)
            serial = USB_PATTERN.search(device_uri).group(1)
            log.debug("udev_serial_no[%s] serial[%s] udev_back_end[%s] back_end[%s]"%(udev_serial_no, serial, udev_back_end, back_end))
            if udev_serial_no == serial and (udev_back_end == back_end or back_end == 'usb'):
                if remove_non_hp_config and printer_name.find('_') == -1 and printer_name.find('-') != -1:
                    log.debug("Removed %s Queue"%printer_name)
                    # remove queues using cups API
                    cups.delPrinter(printer_name)
                else:
                    same_printer_queues.append(printer_name)

        except AttributeError:
            pass

    log.debug(same_printer_queues)
    return same_printer_queues

def check_cups_process():
    cups_running_sts = False
    sts, output = utils.run('lpstat -r')
    if sts == 0 and ('is running' in output):
        cups_running_sts = True
    
    return cups_running_sts


def showPasswordUI(prompt):
    import getpass
    print ""
    print log.bold(prompt)
    username = raw_input("Username: ")
    password = getpass.getpass("Password: ")

    return (username, password)


# Restart cups
def restart_cups():
    if os.path.exists('/etc/init.d/cups'):
        return '/etc/init.d/cups restart'

    elif os.path.exists('/etc/init.d/cupsys'):
        return '/etc/init.d/cupsys restart'

    else:
        return 'killall -HUP cupsd'


# Send dbus event to hpssd on dbus system bus
def send_message(device_uri, printer_name, event_code, username, job_id, title, pipe_name=''):
    log.debug("send_message() entered")
    args = [device_uri, printer_name, event_code, username, job_id, title, pipe_name]
    msg = lowlevel.SignalMessage('/', DBUS_SERVICE, 'Event')
    msg.append(signature='ssisiss', *args)
    SystemBus().send_message(msg)
    log.debug("send_message() returning")


# Usage function
def usage(typ='text'):
    utils.format_text(USAGE, typ, __title__, __mod__, __version__)
    sys.exit(0)

# Systray service. If hp-systray is not running, starts.
def start_systray():
    Systray_Is_Running=False
    status,output = utils.Is_Process_Running('hp-systray')
    if status is False:
        log.debug("hp-systray is not running.")
        if os.getuid() == 0:
            log.error("Run \'hp-systray &\' in a terminal. ")
        else:
            log.debug("Starting hp-systray service")
            child_pid = os.fork()
            if child_pid == 0:
                status,output =utils.run('hp-systray &', True, None, 1, False)
                if status is not 0:
                    log.error("Failed to start \'hp-systray\' service. Manually run \'hp-sysray &\' from terminal as non-root user.")
                sys.exit()
            else:
                time.sleep(1)
                status,output = utils.Is_Process_Running('hp-systray')
                if  status is True:
                    Systray_Is_Running=True
    else:
        Systray_Is_Running=True
        log.debug("hp-systray service is running\n")
    return Systray_Is_Running


USAGE = [ (__doc__, "", "name", True),
          ("Usage: %s [OPTIONS] [SERIAL NO.|USB bus:device]" % __mod__, "", "summary", True),
          utils.USAGE_OPTIONS,
          utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
          utils.USAGE_HELP,
          ("[SERIAL NO.|USB bus:device]", "", "heading", False),
          ("USB bus:device :", """"xxx:yyy" where 'xxx' is the USB bus and 'yyy' is the USB device. (Note: The ':' and all leading zeros must be present.)""", 'option', False),
          ("", "Use the 'lsusb' command to obtain this information.", "option", False),
          ("SERIAL NO.:", '"serial no." (future use)', "option", True),
          utils.USAGE_EXAMPLES,
          ("USB, IDs specified:", "$%s 001:002"%(__mod__), "example", False),
          ("USB, using serial number:", "$%s US12345678A"%(__mod__), "example", False),
          utils.USAGE_SPACE,
          utils.USAGE_NOTES,
          ("1. Using 'lsusb' to obtain USB IDs: (example)", "", 'note', False),
          ("   $ lsusb", "", 'note', False),
          ("         Bus 003 Device 011: ID 03f0:c202 Hewlett-Packard", "", 'note', False),
          ("   $ %s 003:011"%(__mod__), "", 'note', False),
          ("   (Note: You may have to run 'lsusb' from /sbin or another location. Use '$ locate lsusb' to determine this.)", "", 'note', True),
        ]



mod = module.Module(__mod__, __title__, __version__, __doc__, USAGE, (INTERACTIVE_MODE, GUI_MODE), (UI_TOOLKIT_QT3, UI_TOOLKIT_QT4), run_as_root_ok=True, quiet=True)

opts, device_uri, printer_name, mode, ui_toolkit, loc = \
    mod.parseStdOpts('gh',['time-out=', 'timeout='],handle_device_printer=False)


LOG_FILE = "/var/log/hp/hplip_config_usb_printer.log" 
if os.path.exists(LOG_FILE):
    os.remove(LOG_FILE)

log.set_logfile(LOG_FILE)
log.set_where(log.LOG_TO_CONSOLE_AND_FILE)
cmd="chmod 664 "+LOG_FILE
sts,output = utils.run(cmd)
if sts != 0:
    log.warn("Failed to change log file permissions: %s" %output)

cmd="chgrp lp "+LOG_FILE
sts,output = utils.run(cmd)
if sts != 0:
    log.warn("Failed to change log file group permissions: %s" %output)

try:
    import dbus
    from dbus import SystemBus, lowlevel
except ImportError:
        log.error("hp-check-plugin Tool requires dBus and python-dbus")
        sys.exit(1)

try:
    param = mod.args[0]
except IndexError:
    param = ''

log.debug("param=%s" % param)
if len(param) < 1:
    usage()
    sys.exit()

try:
    #*****************************CHECK SMART INSTALL
    try:
        import hpmudext
    except:
        log.error("Failed to import hpmudext")
    else:
        hpmudext.handle_smartinstall()
        

    # ******************************* MAKEURI
    if param:
        device_uri, sane_uri, fax_uri = device.makeURI(param)
    if not device_uri:
        log.error("This is not a valid device")
        sys.exit(0)

    # ******************************* QUERY MODEL AND COLLECT PPDS
    log.debug("\nSetting up device: %s\n" % device_uri)
    back_end, is_hp, bus, model, serial, dev_file, host, zc, port = device.parseDeviceURI(device_uri)

    mq = device.queryModelByURI(device_uri)
    if not mq or mq.get('support-type', SUPPORT_TYPE_NONE) == SUPPORT_TYPE_NONE:
        log.error("Unsupported printer model.")
        sys.exit(1)
    while check_cups_process() is False:
	log.debug("CUPS is not running.. waiting for 30 sec")
        time.sleep(30)

    time.sleep(1)
    norm_model = models.normalizeModelName(model).lower()
    remove_non_hp_config =True
    if not mq.get('fax-type', FAX_TYPE_NONE) in (FAX_TYPE_NONE, FAX_TYPE_NOT_SUPPORTED):
        fax_config_list = get_already_added_queues(norm_model, serial, 'hpfax',remove_non_hp_config)


    printer_config_list = get_already_added_queues(norm_model, serial, back_end, remove_non_hp_config)
    if len(printer_config_list) ==0  or len(printer_config_list) == 0:
        cmd ="hp-setup -i -x -a -q %s"%param
        log.debug("%s"%cmd)
        utils.run(cmd)

        if start_systray():
            printer_name = ""
            username = ""
            send_message( device_uri, printer_name, EVENT_ADD_PRINTQUEUE, username, 0,'')
    else:
        if start_systray():
            printer_name = ""
            username = ""
            send_message( device_uri, printer_name, EVENT_DIAGNOSE_PRINTQUEUE, username, 0,'')

    # Cleaning CUPS created Queues. If any,
    i =0
    while i <24:
        time.sleep(5)
          
        get_already_added_queues(norm_model, serial, 'hpfax',remove_non_hp_config)
        get_already_added_queues(norm_model, serial, 'hp',remove_non_hp_config)
        if i == 0:
            send_message( device_uri, printer_name, EVENT_DIAGNOSE_PRINTQUEUE, username, 0,'')
        i += 1


except KeyboardInterrupt:
    log.error("User exit")

log.debug("Done.")
