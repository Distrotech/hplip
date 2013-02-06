#!/usr/bin/env python
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
# Author: Don Welch, Amarnath Chitumalla
#

__version__ = '15'
__title__ = 'Dependency/Version Check Utility'
__mod__ = 'hp-check'
__doc__ = """Check the existence and versions of HPLIP dependencies. (Run as 'python ./check.py' from the HPLIP tarball before installation.)"""

# Std Lib
import sys
import os
import getopt
import getpass
import commands
import re

# Local
from base.g import *
from base import utils, tui, models,queues
from installer import dcheck
from installer.core_install import *
from prnt import cups
device_avail = False
try:
    from base import device, pml
    # This can fail due to hpmudext not being present
except ImportError:
    log.debug("Device library is not avail.")
else:
    device_avail = True


################ Global variables ############
USAGE = [(__doc__, "", "name", True),
         ("Usage: %s [OPTIONS]" % __mod__, "", "summary", True),
         utils.USAGE_OPTIONS,
         ("Compile-time check:", "-c or --compile", "option", False),
         ("Run-time check:", "-r or --run or --runtime", "option", False),
         ("Compile and run-time checks:", "-b or --both (default)", "option", False),
         ("Fix the found issues on confirmation:", "--fix", "option", False),
         utils.USAGE_LOGGING1, utils.USAGE_LOGGING2, utils.USAGE_LOGGING3,
         utils.USAGE_LOGGING_PLAIN,
         utils.USAGE_HELP,
         
         utils.USAGE_NOTES,
         ("1. For checking for the proper build environment for the HPLIP supplied tarball (.tar.gz or .run),", "", "note", False),
         ("use the --compile or --both switches.", "", "note", False),
         ("2. For checking for the proper runtime environment for a distro supplied package (.deb, .rpm, etc),", "", "note", False),
         ("use the --runtime switch.", "", "note", False),
        ]
        
pat_deviceuri = re.compile(r"""(.*):/(.*?)/(\S*?)\?(?:serial=(\S*)|device=(\S*)|ip=(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}[^&]*)|zc=(\S+))(?:&port=(\d))?""", re.I)
pat_cups_error_log = re.compile("""^loglevel\s?(debug|debug2|warn|info|error|none)""", re.I)
Ver_Func_Pat = re.compile('''FUNC#(.*)''')
exp_pat =re.compile('''.*-G(.*)''')

EXTERNALDEP = 1
GENERALDEP = 2
COMPILEDEP = 3
PYEXT = 4 
SCANCONF = 5
IS_LIBUSB01_ENABLED = 'no'
IS_QUIET_MODE = False
TMP_LOG_CONF_FILE = "/var/log/hp/tmp/hp_check_tmp.log"
############ Functions #########
# Usage function
def usage(typ='text'):
    if typ == 'text':
        utils.log_title(__title__, __version__)

    utils.format_text(USAGE, typ, __title__, __mod__, __version__)
    sys.exit(0)

# Status_Type function. --> Returns the package installed status indformation
def Status_Type(Installedsts, min_ver,Installed_ver):
    if Installedsts is True or Installedsts !=  0:
        if min_ver == '-' or check_version(Installed_ver,min_ver):
            return "OK"
        else:
            return "INCOMPAT"
    else:
        return "MISSING"

#########
def get_HPLIP_version():
    return prop.version
    
# get_comment function --> Returns the 'comments' corresponding to the function.
def get_comment(package, Inst_status, installed_ver):
    comment = "-"
    if package == 'pyqt' or package == 'pyqt4':
        if Inst_status == 'OK':
            if not check_version(installed_ver, '2.3') and check_version(installed_ver, '2.2'):
                comment = "Fax is not supported if version is lessthan 2.3"
            elif not check_version(installed_ver, '2.2'):
                comment = "Python Programming is not supported if version is lessthan 2.2" 
    elif package == 'hpaio':
        if Inst_status == 'OK':
            comment = "'hpaio found in /etc/sane.d/dll.conf'"
        else:
            comment = "'hpaio not found in /etc/sane.d/dll.conf. hpaio needs to be added in this file.'"
    elif package == 'cupsext' or package == 'pcardext' or package == 'hpmudext':
        if Inst_status != 'OK':
            comment = "'Not Found or Failed to load, Please reinstall HPLIP'"
    elif package =='cups':
        if Inst_status != 'OK':
            comment = "'CUPS may not be installed or not running'"
        else:
            comment = "'CUPS Scheduler is running'"
    elif package == 'libusb' and IS_LIBUSB01_ENABLED == "yes":
        if Inst_status != 'OK':
            comment = "'libusb-1.0 needs to be installed'"
    elif package == 'dbus':
        if Inst_status != 'OK':
            comment = "'DBUS may not be installed or not running'"
        else:
            comment = "-"
    else:
        if Inst_status != 'OK':
            comment = "'%s needs to be installed'"%package
    return comment


#Restart Cups if not running
def start_service(core, service_name=None):
    ret_Val = False
    if not service_name:
        return ret_Val

    cmd="%s"
    if core.su_sudo_str() == 'su':
        cmd = "su -c '%s'"
    else:
        cmd = "sudo %s"
        
    if utils.which('service'):
        cmd_status = cmd%("service %s status"%service_name)
        log.info("cmd_status=%s"%cmd_status)
        sts,out = core.run(cmd_status)
        if sts ==0:
            if 'stop' in out:
                cmd_start = cmd%("service %s start"%service_name)
                log.info("cmd_start=%s"%cmd_start)
                sts,out = core.run(cmd_start)
                if sts ==0:
                    ret_Val = True
            else:
                ret_Val = True
    else:
        if service_name == 'cups':
            cmd = 'lpstat -r'
            sts,out = core.run(cmd)
            if sts ==0 and 'is running' in out:
                ret_Val = True

    return ret_Val

#password_entry funtion
def password_entry():
    return getpass.getpass(log.bold("Please enter the root/superuser password: "))
    
# password_user_entry function
def password_user_entry():
    return getpass.getpass(log.bold("Please enter the sudoer (%s)'s password: " % os.getenv('USER')))

#progress_callback function
def progress_callback(cmd="", desc="Working..."):
    if cmd:
        log.info("%s (%s)" % (cmd, desc))
    else:
        log.info(desc)

#check_permissions Function --> prompt for password and checks the user permission.
def check_permissions(core):
    result = False
    if not core.running_as_root():
        su_sudo = core.get_distro_data('su_sudo')
        if su_sudo == "sudo":
            tui.title("ENTER SUDO PASSWORD")
            result = core.check_password(password_user_entry, progress_callback)
        else:
            tui.title("ENTER ROOT/SUPERUSER PASSWORD")
            result = core.check_password(password_entry, progress_callback)
    else:
        result = True
        
    if not result:
        log.error("3 incorrect attempts. (or) Insufficient permissions(i.e. try with sudo user).\nExiting.")
        sys.exit(1)    
    return result

    
#check_user_groups function checks required groups and returns missing list.
def check_user_groups(str_grp, avl_grps):
    result = False
    exp_grp_list=[]
    if str_grp and exp_pat.search(str_grp):
        grps = exp_pat.search(str_grp).group(1)
        grps =re.sub(r'\s', '', str(grps))
        exp_grp_list = grps.split(',')
    else:
        exp_grp_list.append('lp')

    log.debug("Requied groups list =[%s]"%exp_grp_list)

    avl_grps = avl_grps.rstrip('\r\n')
    grp_list= avl_grps.split(' ')
    for  g in grp_list:
        grp_index = 0
        for p in exp_grp_list:
            if g == p:
                del exp_grp_list[grp_index]
                break
            grp_index +=1

    if len(exp_grp_list) == 0:
        result = True
    missing_groups_str=''
    for a in exp_grp_list:
        if missing_groups_str:
            missing_groups_str += ','
        missing_groups_str += a
    return result ,missing_groups_str

    


# parseDeviceURI function to get the device details.
def parseDeviceURI(device_uri):
    m = pat_deviceuri.match(device_uri)
    if m is None:
        raise Error(ERROR_INVALID_DEVICE_URI)
    back_end = m.group(1).lower() or ''
    is_hp = (back_end in ('hp', 'hpfax', 'hpaio'))
    bus = m.group(2).lower() or ''
    if bus not in ('usb', 'net', 'bt', 'fw', 'par'):
        raise Error(ERROR_INVALID_DEVICE_URI)
    model = m.group(3) or ''
    serial = m.group(4) or ''
    dev_file = m.group(5) or ''
    host = m.group(6) or ''
    zc = ''
    if not host:
        zc = host = m.group(7) or ''
    port = m.group(8) or 1
    if bus == 'net':
        try:
            port = int(port)
        except (ValueError, TypeError):
            port = 1

        if port == 0:
            port = 1
    return back_end, is_hp, bus, model, serial, dev_file, host, zc, port

# close package manager
def close_package_managers(core):
    pid, cmdline = core.check_pkg_mgr()
    while pid:
        ok, user_input = tui.enter_choice("A package manager '%s' appears to be running. Please quit the package manager and press enter to continue (i=ignore, r=retry*, f=force, q=quit) :" % cmdline, ['i', 'r', 'q', 'f'], 'r')

        if not ok: sys.exit(0)
        if user_input == 'i':
            log.warn("Ignoring running package manager. Some package operations may fail.")
            break

        if user_input == 'f':
            ok, ans = tui.enter_yes_no("\nForce quit of package manager '%s'" % cmdline, 'y')
            if not ok: sys.exit(0)
            if ans:
                cmd = core.su_sudo() % ("kill %d" % pid)
                status, output = core.run(cmd)
                if status != 0:
                    log.error("Failed to kill process. You may need to manually quit the program.")

        pid, cmdline = core.check_pkg_mgr()

# This always returns 1.0, TBD: need to get libusb-1.0 version information dynamically.
def get_libusb_version():
    if IS_LIBUSB01_ENABLED == "yes":
        return get_version('libusb-config --version')
    else:
        return '1.0'


# This updates the config log file
def update_log_file(log_conf, section, key, value):
    if IS_QUIET_MODE:
        log_conf.set(section, key, value)


########## Classes ###########
#DependenciesCheck class derived from CoreInstall
class DependenciesCheck(CoreInstall):
    def __init__(self,mode=MODE_CHECK, ui_mode=INTERACTIVE_MODE, ui_toolkit='qt4'):
        CoreInstall.__init__(self,mode,ui_mode,ui_toolkit)
        self.hplip_dependencies ={ EXTERNALDEP:
             {
#            <packageName>: (<Is Req/Opt Pack>, <Module>, <Package description>, <Installed check>, <min vrsion>, <cmd for installed version>),
            'dbus':             (True,  ['fax'], "DBus", self.check_dbus,'-','dbus-daemon --version'),
            'cups' :            (True,  ['base'], 'CUPS', self.check_cups,'1.1','cups-config --version'),
            'gs':               (True,  ['base'], "Ghostscript", self.check_gs,'7.05','gs --version'),
            'policykit':        (False, ['gui_qt4'], "Admin-Policy-framework", self.check_policykit,'-','pkexec --version'), # optional for non-sudo behavior of plugins (only optional for Qt4 option)
            'xsane':            (False, ['scan'], "SANE-GUI", self.check_xsane,'0.9','FUNC#get_xsane_version'),
            'scanimage':        (False, ['scan'], "Shell-Scanning", self.check_scanimage,'1.0','scanimage --version'),
            'network':        (False, ['network'], "Network-wget", self.check_wget,'-','wget --version'),
            },
            GENERALDEP:
            {'libpthread':       (True,  ['base'], "POSIX-Threads-Lib", self.check_libpthread,'-','FUNC#get_libpthread_version'),
            'libusb':           (True,  ['base'], "USB-Lib", self.check_libusb,'-','FUNC#get_libusb_version'),
            'libcrypto':        (True,  ['network'], "OpenSSL-Crypto-Lib", self.check_libcrypto,'-','openssl version'),
            'libjpeg':          (True,  ['base'], "JPEG-Lib", self.check_libjpeg,'-',None),
            'libnetsnmp-devel': (True,  ['network'], "SNMP-Networking-SDK", self.check_libnetsnmp,'5.0.9','net-snmp-config --version'),
            'cups-image':       (True,  ['base'], "CUPS-Image-Lib", self.check_cups_image,'-','cups-config --version'),
            'cups-devel':       (True,  ['base'], 'CUPS-SDK', self.check_cups_devel,'-','cups-config --version'),
            'cups-ddk':          (False, ['base'], "CUPS-DDK", self.check_cupsddk,'-',None), # req. for .drv PPD installs
            'python-dbus':      (True,  ['fax'], "Python-DBUS", self.check_python_dbus,'0.80.0','FUNC#get_python_dbus_ver'),
            'pyqt4':            (True,  ['gui_qt4'], "Python-Qt4", self.check_pyqt4,'4.0','FUNC#get_pyQt4_version'), # PyQt 4.x )
            'pyqt4-dbus' :      (True,  ['gui_qt4'], "PyQt4-DBUS", self.check_pyqt4_dbus,'4.0','FUNC#get_pyQt4_version'), 
            'pyqt':            (True,  ['gui_qt'], "Python-Qt", self.check_pyqt,'2.3','FUNC#get_pyQt_version'), 
            'python-devel' :    (True,  ['base'], "Python-SDK", self.check_python_devel,'2.2','python --version'),
            'python-notify' :   (False, ['gui_qt4'], "Desktop-notifications", self.check_pynotify,'-','python-notify --version'), # Optional for libnotify style popups from hp-systray
            'python-xml'  :     (True,  ['base'], "Python-XML-Lib", self.check_python_xml,'-','FUNC#get_python_xml_version'),
            'pil':              (False, ['scan'], "Python-Image-Lib", self.check_pil,'-','FUNC#get_pil_version'), #required for commandline scanning with hp-scan
            'sane':             (True,  ['scan'], "Scan-Lib", self.check_sane,'-','sane-config --version'),
            'sane-devel' :      (True,  ['scan'], "SANE-SDK", self.check_sane_devel,'-','sane-config --version'),
            'reportlab':        (False, ['fax'], "Python-PDF-Lib", self.check_reportlab,'2.0','FUNC#get_reportlab_version'),
            },
            COMPILEDEP:
            { 'gcc' :             (True,  ['base'], 'gcc-Compiler', self.check_gcc, '-','gcc --version'),
            'libtool':          (True,  ['base'], "Build-tools", self.check_libtool,'-','libtool --version'),
            'make' :            (True,  ['base'], "GNU-Build-tools", self.check_make,'3.0','make --version'),
            },
            PYEXT: 
             { 'cupsext' :         (True,  ['base'], 'CUPS-Extension', self.check_cupsext,'-','FUNC#get_HPLIP_version'),
            'hpmudext' :        (True,  ['base'], 'IO-Extension', self.check_hpmudext,'-','FUNC#get_HPLIP_version'),
            'pcardext' :        (True,  ['base'], 'PhotoCard-Extension', self.check_pcardext,'-','FUNC#get_HPLIP_version'),
            },
            SCANCONF:
            { 'hpaio' :           (True,  ['scan'], 'HPLIP-SANE-Backend', self.check_hpaio,'-','FUNC#get_HPLIP_version'), 
            'scanext' :           (True,  ['scan'], 'Scan-SANE-Extension', self.check_scanext,'-','FUNC#get_HPLIP_version'), 
            }
        }

        self.version_func={
            'FUNC#get_python_dbus_ver':get_python_dbus_ver,
            'FUNC#get_pyQt4_version':get_pyQt4_version,
            'FUNC#get_pyQt_version':get_pyQt_version,
            'FUNC#get_reportlab_version':get_reportlab_version,
            'FUNC#get_xsane_version':get_xsane_version,
            'FUNC#get_pil_version':get_pil_version,
            'FUNC#get_libpthread_version':get_libpthread_version,
            'FUNC#get_python_xml_version':get_python_xml_version,
            'FUNC#get_HPLIP_version':get_HPLIP_version,
            'FUNC#get_libusb_version':get_libusb_version,
            }
    

############ Variables #######################
req_deps_to_be_installed=[]
opt_deps_to_be_installed=[]
cmds_to_be_run=[]
overall_install_cmds={}
cups_ddk_not_req = False
num_errors = 0
num_warns = 0
hpmudext_avail = False
fmt = True
Fix_Found_Problems = False
plugin_error = False
user_grp_error = False
add_user_to_group = None
time_flag = DEPENDENCY_RUN_AND_COMPILE_TIME
Is_cups_running = True

############ Main #######################
try:
    log.set_module(__mod__)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hl:gtcrbsi', ['help', 'help-rest', 'help-man', 'help-desc', 'logging=', 'run', 'runtime', 'compile', 'both','fix'])

    except getopt.GetoptError, e:
        log.error(e.msg)
        usage()
        sys.exit(1)

    if os.getenv("HPLIP_DEBUG"):
        log.set_level('debug')

    log_level = 'info'
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
        elif o == '--help-rest':
            usage('rest')
        elif o == '--help-man':
            usage('man')
        elif o == '--help-desc':
            print __doc__,
            sys.exit(0)
        elif o in ('-l', '--logging'):
            log_level = a.lower().strip()
        elif o == '-g':
            log_level = 'debug'
        elif o == '-t':
            fmt = False
        elif o in ('-c', '--compile'):
            time_flag = DEPENDENCY_COMPILE_TIME
        elif o in ('-r', '--runtime', '--run'):
            time_flag = DEPENDENCY_RUN_TIME
        elif o in ('-b', '--both'):
            time_flag = DEPENDENCY_RUN_AND_COMPILE_TIME
        elif o == '--fix':
            Fix_Found_Problems = True
        elif o == '-s':
            IS_QUIET_MODE = True


    if not log.set_level(log_level):
        usage()

    if not fmt:
        log.no_formatting()
        
    if not IS_QUIET_MODE:
        utils.log_title(__title__, __version__)

        log.info(log.bold("Note: hp-check can be run in three modes:"))

        for l in tui.format_paragraph("1. Compile-time check mode (-c or --compile): Use this mode before compiling the HPLIP supplied tarball (.tar.gz or .run) to determine if the proper dependencies are installed to successfully compile HPLIP."):
            log.info(l)

        for l in tui.format_paragraph("2. Run-time check mode (-r or --run): Use this mode to determine if a distro supplied package (.deb, .rpm, etc) or an already built HPLIP supplied tarball has the proper dependencies installed to successfully run."):
            log.info(l)

        for l in tui.format_paragraph("3. Both compile- and run-time check mode (-b or --both) (Default): This mode will check both of the above cases (both compile- and run-time dependencies)."):
            log.info(l)

        log.info()
        for l in tui.format_paragraph("Check types:"):
            log.info(l)
        for l in tui.format_paragraph("a. EXTERNALDEP - External Dependencies"):
            log.info(l)
        for l in tui.format_paragraph("b. GENERALDEP  - General Dependencies (required both at compile and run time)"):
            log.info(l)
        for l in tui.format_paragraph("c. COMPILEDEP  - Compile time Dependencies"):
            log.info(l)
        for l in tui.format_paragraph("d. [All are run-time checks]"):
            log.info(l)
        for l in tui.format_paragraph("PYEXT\nSCANCONF\nQUEUES\nPERMISSION"):
            log.info(l)

        log.info()
        log.info("Status Types:")
        log.info("    OK")
        log.info("    MISSING       - Missing Dependency or Permission or Plug-in")
        log.info("    INCOMPAT      - Incompatible dependency-version or Plugin-version")
        log.info()

    log_file = os.path.abspath('./hp-check.log')
    log.info(log.bold("Saving output in log file: %s" % log_file))
    log.debug("Log file=%s" % log_file)
    if os.path.exists(log_file):
        os.remove(log_file)
    
    quiet_mode_log_conf =None
    log.set_logfile(log_file)    
    if IS_QUIET_MODE:
        try:
           fp = open(TMP_LOG_CONF_FILE, "w")
           os.chmod(TMP_LOG_CONF_FILE,0666)
           fp.close()
        except (OSError, IOError):
           log.debug("Unable to open file %s for writing." % TMP_LOG_CONF_FILE)

        quiet_mode_log_conf = ConfigBase(TMP_LOG_CONF_FILE)
        log.set_where(log.LOG_TO_FILE)
    else:
        log.set_where(log.LOG_TO_CONSOLE_AND_FILE)
    log.info("\nInitializing. Please wait...")
    ui_toolkit = sys_conf.get('configure','ui-toolkit')
    core =  DependenciesCheck(MODE_CHECK,INTERACTIVE_MODE,ui_toolkit)
    core.init()
    core.set_plugin_version()

    IS_LIBUSB01_ENABLED = sys_conf.get('configure', 'libusb01-build', 'no')
    package_mgr_cmd = core.get_distro_data('package_mgr_cmd')
    vrs =core.get_distro_data('versions_list')
    supported_distro_vrs= core.distro_version
    if core.distro_version not in vrs and len(vrs):
        supported_distro_vrs= vrs[len(vrs)-1]
        log.warn(log.bold("%s-%s version is not supported. Using %s-%s versions dependencies to verify and install..." \
                 %(core.distro_name, core.distro_version, core.distro_name, supported_distro_vrs)))
      
    tui.header("SYSTEM INFO")
    Sts, Kernel_info =core.run("uname -r -v -o")
    Sts, Host_info =core.run("uname -n")
    Sts, Proc_info =core.run("uname -r -v -o")
    log.info(" Kernel: %s Host: %s Proc: %s Distribution: %s %s"\
         %(Kernel_info,Host_info,Proc_info,core.distro_name, core.distro_version))

    
    tui.header("HPLIP CONFIGURATION")
    v = sys_conf.get('hplip', 'version')
    if v:
        home = sys_conf.get('dirs', 'home')
        log.info("HPLIP-Version: HPLIP %s" %v)
        log.info("HPLIP-Home: %s" %home)
        if core.is_auto_installer_support():
            log.info("HPLIP-Installation: Auto installation is supported for %s distro  %s version " %(core.distro_name, core.distro_version))
        else:
            log.warn("HPLIP-Installation: Auto installation is not supported for %s distro  %s version " %(core.distro_name, core.distro_version))


        log.info()
        log.info(log.bold("Current contents of '/etc/hp/hplip.conf' file:"))
        try:
            output = file('/etc/hp/hplip.conf', 'r').read()
        except (IOError, OSError), e:
            log.error("Could not access file: %s. Check HPLIP installation." % e.strerror)
            num_errors += 1
        else:
            log.info(output)

        log.info()
        log.info(log.bold("Current contents of '/var/lib/hp/hplip.state' file:"))
        try:
            output = file(os.path.expanduser('/var/lib/hp/hplip.state'), 'r').read()
        except (IOError, OSError), e:
            log.info("Plugins are not installed. Could not access file: %s" % e.strerror)
        else:
            log.info(output)

        log.info()
        log.info(log.bold("Current contents of '~/.hplip/hplip.conf' file:"))
        try:
            output = file(os.path.expanduser('~/.hplip/hplip.conf'), 'r').read()
        except (IOError, OSError), e:
            log.warn("Could not access file: %s" % e.strerror)
            num_warns += 1
        else:
            log.info(output)

        scanning_enabled = utils.to_bool(sys_conf.get('configure', 'scanner-build', '0'))
        log.info(" %-20s %-20s %-10s %-10s %-10s %-10s %s"%( "<Package-name>", " <Package-Desc>", "<Required/Optional>", "<Min-Version>","<Installed-Version>", "<Status>", "<Comment>"))
        opt_missing_index=1
        req_missing_index=1
        for s in core.hplip_dependencies:
            if s == EXTERNALDEP: 
                if time_flag == DEPENDENCY_RUN_AND_COMPILE_TIME or time_flag == DEPENDENCY_RUN_TIME:
                    tui.header(" External Dependencies")
                else: continue
            elif s == GENERALDEP: 
                if time_flag == DEPENDENCY_RUN_AND_COMPILE_TIME or time_flag == DEPENDENCY_RUN_TIME:
                    tui.header(" General Dependencies")
                else: continue
            elif s == COMPILEDEP: 
                if time_flag == DEPENDENCY_RUN_AND_COMPILE_TIME or time_flag == DEPENDENCY_COMPILE_TIME:
                    tui.header(" Compile Time Dependencies")
                else: continue
            elif s == PYEXT: tui.header(" Python Extentions")
            elif s == SCANCONF: tui.header(" Scan Configuration")
            else: tui.header(" Other Dependencies")
            for d in core.hplip_dependencies[s]:
                if d == 'cups-ddk' and cups_ddk_not_req == True:
                    continue
                elif ui_toolkit != 'qt4' and ui_toolkit != 'qt3' and d == 'pyqt':
                    continue
                elif d == 'pyqt' and ui_toolkit == 'qt4':
                    continue
                elif d == 'pyqt4' and ui_toolkit == 'qt3':
                    continue
                elif d == 'hpaio' and not scanning_enabled:
                    continue
                elif core.distro_name =="rhel" and "5." in core.distro_version:
                    if d in ['dbus','python-devel','python-dbus','pyqt4-dbus','libnetsnmp-devel','gcc','make','reportlab','policykit','sane-devel','cups-ddk']:
                        continue

                if core.hplip_dependencies[s][d][5] is None:
                    installed_ver = '-'
                elif Ver_Func_Pat.search(core.hplip_dependencies[s][d][5]):
                    if core.hplip_dependencies[s][d][5] in core.version_func:
                        installed_ver = core.version_func[core.hplip_dependencies[s][d][5]]()
                    else:
                        installed_ver = '-'
                else:
                    installed_ver = get_version(core.hplip_dependencies[s][d][5])
                Status = Status_Type(core.hplip_dependencies[s][d][3](),core.hplip_dependencies[s][d][4],installed_ver) 
                comment = get_comment(d, Status, installed_ver)
                packages_to_install, commands=[],[]
                if core.is_auto_installer_support():
                    packages_to_install, commands = core.get_dependency_data(d)
                    if not packages_to_install and d == 'hpaio':
                        packages_to_install.append(d)
                else:
                    packages_to_install, commands = core.get_dependency_data(d,supported_distro_vrs)
                    if not packages_to_install and d == 'hpaio':
                        packages_to_install.append(d)
                if core.hplip_dependencies[s][d][0]:
                    package_type = "REQUIRED"
                    if Status != 'OK':
                        for pkg in packages_to_install:
                            req_deps_to_be_installed.append(pkg)
                        for cmd in commands:
                            cmds_to_be_run.append(cmd)
#                        log.info("commands =%s"%commands)
                else:
                    package_type = "OPTIONAL"
                    if Status != 'OK':
                        for pkg in packages_to_install:
                            opt_deps_to_be_installed.append(pkg)
                        for cmd in commands:
                            cmds_to_be_run.append(cmd)
                if d == 'cups' and Status != 'OK':
                    Is_cups_running = False
                if d == 'cups' and check_version(installed_ver,'1.4'):
                    cups_ddk_not_req = True
                    log.debug("cups -ddk not required as cups version [%s] is => 1.4 "%installed_ver)
                if d == 'hpmudext' and Status == 'OK':
                    hpmudext_avail = True
                    
                if Status == 'OK':
                    log.info(" %-20s %-25s %-15s %-15s %-15s %-10s %s" %(d,core.hplip_dependencies[s][d][2], package_type,core.hplip_dependencies[s][d][4],installed_ver,Status,comment))
                else:
                    log.info(log.red(" error: %-13s %-25s %-15s %-15s %-15s %-10s %s" %(d,core.hplip_dependencies[s][d][2], package_type,core.hplip_dependencies[s][d][4],installed_ver,Status,comment)))
                    if package_type == "OPTIONAL":
                        for pkg in packages_to_install:
                            update_log_file(quiet_mode_log_conf, "OPTIONAL_MISSING_PACKAGE","package%d"%opt_missing_index, pkg)
                            opt_missing_index += 1
                    else:
                        for pkg in packages_to_install:
                            update_log_file(quiet_mode_log_conf, "REQUIRED_MISSING_PACKAGE","package%d"%req_missing_index, pkg)
                            req_missing_index += 1


        if scanning_enabled:
            tui.header("DISCOVERED SCANNER DEVICES")
            if utils.which('scanimage'):
                status, output = utils.run("scanimage -L")
                if status != 0 :
                    log.error("Failed to get Scanners information.")
                elif 'No scanners were identified' in output:
                    log.info("No Scanner found.")
                else:
                    log.info(output)

        if device_avail:
            #if prop.par_build:
                #tui.header("DISCOVERED PARALLEL DEVICES")
                #devices = device.probeDevices(['par'])
                #if devices:
                    #f = tui.Formatter()
                    #f.header = ("Device URI", "Model")
                    #for d, dd in devices.items():
                        #f.add((d, dd[0]))
                    #f.output()
                #else:
                    #log.info("No devices found.")
                    #if not core.have_dependencies['ppdev']:
                        #log.error("'ppdecmds_to_be_runv' kernel module not loaded.")

            if prop.usb_build:
                tui.header("DISCOVERED USB DEVICES")

                devices = device.probeDevices(['usb'])

                if devices:
                    f = tui.Formatter()
                    f.header = ("Device URI", "Model")

                    for d, dd in devices.items():
                        f.add((d, dd[0]))

                    f.output()

                else:
                    log.info("No devices found.")


        tui.header("INSTALLED CUPS PRINTER QUEUES")

        lpstat_pat = re.compile(r"""(\S*): (.*)""", re.IGNORECASE)
        status, output = utils.run('lpstat -v')
        log.info()

        cups_printers = []
        for p in output.splitlines():
            try:
                match = lpstat_pat.search(p)
                printer_name = match.group(1)
                device_uri = match.group(2)
                cups_printers.append((printer_name, device_uri))
            except AttributeError:
                pass

        log.debug(cups_printers)
        if cups_printers:
            #non_hp = False
            for p in cups_printers:
                printer_name, device_uri = p

                if device_uri.startswith("cups-pdf:/") or \
                    device_uri.startswith('ipp://'):
                    continue

                try:
                    back_end, is_hp, bus, model, serial, dev_file, host, zc, port = \
                        parseDeviceURI(device_uri)
                except Error:
                    back_end, is_hp, bus, model, serial, dev_file, host, zc, port = \
                        '', False, '', '', '', '', '', '', 1

                #print back_end, is_hp, bus, model, serial, dev_file, host, zc, port

                log.info(log.bold(printer_name))
                log.info(log.bold('-'*len(printer_name)))

                x = "Unknown"
                if back_end == 'hpfax':
                    x = "Fax"
                elif back_end == 'hp':
                    x = "Printer"

                log.info("Type: %s" % x)

                #if is_hp:
                #    x = 'Yes, using the %s: CUPS backend.' % back_end
                #else:
                #    x = 'No, not using the hp: or hpfax: CUPS backend.'
                #    non_hp = True

                #log.info("Installed in HPLIP?: %s" % x)
                log.info("Device URI: %s" % device_uri)

                ppd = os.path.join('/etc/cups/ppd', printer_name + '.ppd')

                if os.path.exists(ppd):
                    log.info("PPD: %s" % ppd)
                    nickname_pat = re.compile(r'''\*NickName:\s*\"(.*)"''', re.MULTILINE)
                    try:
                        f = file(ppd, 'r').read(4096)
                    except IOError:
                        log.warn("Failed to read %s ppd file"%ppd)
                        desc = ''
                    else:
                        try:
                            desc = nickname_pat.search(f).group(1)
                        except AttributeError:
                            desc = ''

                    log.info("PPD Description: %s" % desc)

                    status, output = utils.run('lpstat -p%s' % printer_name)
                    log.info("Printer status: %s" % output.replace("\n", ""))

                    if back_end == 'hpfax' and not 'HP Fax' in desc:
                        num_errors += 1
                        log.error("Incorrect PPD file for fax queue '%s'. Fax queues must use 'HP-Fax-hplip.ppd'." % printer_name)

                    elif back_end == 'hp' and 'HP Fax' in desc:
                        num_errors += 1
                        log.error("Incorrect PPD file for a print queue '%s'. Print queues must not use 'HP-Fax-hplip.ppd'." % printer_name)

                    elif back_end not in ('hp', 'hpfax'):
                        log.warn("Printer is not HPLIP installed. Printers must use the hp: or hpfax: CUPS backend for HP-Devices.")
                        num_warns += 1

                if device_avail and is_hp:
                    d = None
                    try:
                        try:
                            d = device.Device(device_uri,None, None, None, True)
                        except Error:
                            log.error("Device initialization failed.")
                            continue

                        plugin = d.mq.get('plugin', PLUGIN_NONE)
                        if plugin in (PLUGIN_REQUIRED, PLUGIN_OPTIONAL):
                            update_log_file(quiet_mode_log_conf, "PLUGIN","plugin_printer_present", True)
                            plugin_sts = core.check_for_plugin()
                            if plugin_sts == PLUGIN_INSTALLED:
                                if plugin == PLUGIN_REQUIRED:
                                    log.info("Required plug-in status: Installed")
                                else:
                                    log.info("Optional plug-in status: Installed")
                            elif plugin_sts == PLUGIN_VERSION_MISMATCH:
                                num_warns += 1
                                plugin_error = True
                                log.warn("plug-in status: Version mismatch")
                                
                            else:
                                plugin_error = True
                                if plugin == PLUGIN_REQUIRED:
                                    num_errors += 1
                                    log.error("Required plug-in status: Not installed")
                                else:
                                    num_warns +=1
                                    log.warn("Optional plug-in status: Not installed")


                        if bus in ('par', 'usb'):
                            try:
                                d.open()
                            except Error, e:
                                log.error(e.msg)
                                deviceid = ''
                            else:
                                deviceid = d.getDeviceID()
                                log.debug(deviceid)

                            #print deviceid
                            if not deviceid:
                                log.error("Communication status: Failed")
                                update_log_file(quiet_mode_log_conf, "DEVICE_COMM_ERRORS",printer_name, device_uri)
                                num_errors += 1
                            else:
                                log.info("Communication status: Good")

                        elif bus == 'net':
                            try:
                                error_code, deviceid = d.getPML(pml.OID_DEVICE_ID)
                            except Error:
                                pass

                            #print error_code
                            if not deviceid:
                                log.error("Communication status: Failed")
                                update_log_file(quiet_mode_log_conf, "DEVICE_COMM_ERRORS",printer_name, device_uri)
                                num_errors += 1
                            else:
                                log.info("Communication status: Good")

                    finally:
                        if d is not None:
                            d.close()

                log.info()

        else:
            log.warn("No queues found.")

        tui.header("PERMISSION")
        sts,avl_grps_out =core.run('groups')
        add_user_to_group = core.get_distro_ver_data('add_user_to_group', '',supported_distro_vrs)
        sts, out = check_user_groups(add_user_to_group, avl_grps_out) 
        if sts:
            log.info("%-15s %-30s %-15s %-8s %-8s %-8s %s"%("groups", "user-groups","Required", "-","-", "OK",avl_grps_out))
        else:
            log.info(log.red("error: %-8s %-30s %-15s %-8s %-8s %-8s %s"%("groups", "user-groups", "Required","-", "-", "MISSING", out)))
            num_errors += 1
            user_grp_error = True
            update_log_file(quiet_mode_log_conf, "GROUPS","missing-user-groups", out)
            update_log_file(quiet_mode_log_conf, "GROUPS","missing-user-groups-cmd", add_user_to_group)

        if hpmudext_avail:
            lsusb = utils.which('lsusb')
            if lsusb:
                lsusb = os.path.join(lsusb, 'lsusb')
                status, output = utils.run("%s -d03f0:" % lsusb)

                if output:
                    lsusb_pat = re.compile("""^Bus\s([0-9a-fA-F]{3,3})\sDevice\s([0-9a-fA-F]{3,3}):\sID\s([0-9a-fA-F]{4,4}):([0-9a-fA-F]{4,4})(.*)""", re.IGNORECASE)
                    log.debug(output)
                    try:
                        import hpmudext
                    except ImportError:
                        log.error("NOT FOUND OR FAILED TO LOAD! Please reinstall HPLIP and check for the proper installation of hpmudext.")

                    for o in output.splitlines():
                        ok = True
                        match = lsusb_pat.search(o)

                        if match is not None:
                            bus, dev, vid, pid, mfg = match.groups()
                            #log.info("\nHP Device 0x%x at %s:%s: " % (int(pid, 16), bus, dev))
                            result_code, deviceuri = hpmudext.make_usb_uri(bus, dev)

                            if result_code == hpmudext.HPMUD_R_OK:
                            #    log.info("    Device URI: %s" %  deviceuri)
                                d = None
                                try:
                                    d = device.Device(deviceuri,None, None, None, True)
                                except Error:
                                    continue
                                if not d.supported:
                                    continue
                            else:
                                log.warn("    Device URI: (Makeuri FAILED)")
                                continue
                            printers = cups.getPrinters()
                            printer_name=None
                            for p in printers:
                                if p.device_uri == deviceuri:
                                    printer_name=p.name
                                    break

                            devnode = os.path.join("/", "dev", "bus", "usb", bus, dev)

                            if not os.path.exists(devnode):
                                devnode = os.path.join("/", "proc", "bus", "usb", bus, dev)

                            if os.path.exists(devnode):
                               # log.debug("    Device node: %s" % devnode)
                                st_mode, st_ino, st_dev, st_nlink, st_uid, st_gid, \
                                   st_size, st_atime, st_mtime, st_ctime =  os.stat(devnode)

                                getfacl = utils.which('getfacl')
                                if getfacl:
                                    getfacl = os.path.join(getfacl, "getfacl")
                                   # log.debug("%s %s" % (getfacl, devnode))
                                    status, output = utils.run("%s %s" % (getfacl, devnode))
                                    getfacl_out_list = output.split('\r\n')

                                   # log.debug(output)
                                    out =''
                                    for g in getfacl_out_list:
                                        if 'getfacl' not in g and '' is not g and 'file' not in g:
                                            pat = re.compile('''.*:(.*)''')
                                            if pat.search(g):
                                                out = out +' '+ pat.search(g).group(1)
                                    log.info("%-15s %-30s %-15s %-8s %-8s %-8s %s"%("USB", printer_name, "Required", "-", "-", "OK", "Node:'%s' Perm:'%s'"%(devnode,out)))
                                else:
                                    log.info("%-15s %-30s %-15s %-8s %-8s %-8s %s"%("USB", printer_name, "Required","-","-","OK", "Node:'%s' Mode:'%s'"%(devnode,st_mode&0777)))

        selinux_file = '/etc/selinux/config'
        disable_selinux=False
        if os.path.exists(selinux_file):
            tui.header("SELINUX")
            try:
                selinux_fp = file(selinux_file, 'r')
            except IOError:
                log.error("Failed to open %s file."%selinux_file)
            else:
                for line in selinux_fp:
                    line=re.sub(r'\s','',line)
                    if line == "SELINUX=enforcing":
                        num_warns += 1
                        disable_selinux = True
                        log.warn("%-12s %-12s %-10s %-3s %-3s %-8s %s" \
                                      %("SELinux",  "enabled", "Optional", "-", "-", "INCOMPAT", "'SELinux needs to be disabled for Plugin printers and Fax functionality.'"))
                        update_log_file(quiet_mode_log_conf, "GROUPS","selinux_status", "enabled")
                        break
                if disable_selinux == False:
                    log.info("%-15s %-15s %-10s %-3s %-3s %-8s %s"\
                                              %("SELinux",  "disabled", "Optional", "-", "-", "OK", "-"))
                                              
        package_mgr_cmd = core.get_distro_data('package_mgr_cmd')
        pre_depend_cmd  = core.get_distro_data('pre_depend_cmd')
        tui.header("SUMMARY")
#        if IS_QUIET_MODE:
#            log.set_where(log.LOG_TO_CONSOLE_AND_FILE)
#            log.debug("")
        log.info(log.bold("Missing Required Dependencies"))
        log.info(log.bold('-'*len("Missing Required Dependencies")))
        
        if len(req_deps_to_be_installed) == 0:
            log.info("None")
        else:
            for packages_to_install in req_deps_to_be_installed:
                if package_mgr_cmd:
                    overall_install_cmds[packages_to_install] =utils.cat(package_mgr_cmd)
                else:
                    overall_install_cmds[packages_to_install] =packages_to_install
                    
                if packages_to_install == 'cups':
                    log.error("'%s' package is missing or '%s' service is not running."%(packages_to_install,packages_to_install))
                else:
                    log.error("'%s' package is missing/incompatible "%packages_to_install)
                num_errors += 1

        log.info("")
        log.info(log.bold("Missing Optional Dependencies"))
        log.info(log.bold('-'*len("Missing Optional Dependencies")))
        if len(opt_deps_to_be_installed) == 0:
            log.info("None")
        else:
            for packages_to_install in opt_deps_to_be_installed:
                if package_mgr_cmd:
                    overall_install_cmds[packages_to_install] =utils.cat(package_mgr_cmd)
                else:
                    overall_install_cmds[packages_to_install] =packages_to_install

                log.error("'%s' package is missing/incompatible "%packages_to_install)
                num_errors += 1
        log.info()
        
    else:
        log.error("HPLIP not found.")
        num_errors += 1
        
    if IS_QUIET_MODE:
        log.set_where(log.LOG_TO_FILE)
        
    log.info()
    log.info("Total Errors: %d" % num_errors)
    log.info("Total Warnings: %d" % num_warns)
    log.info()
    if Fix_Found_Problems:
        queues.main_function(INTERACTIVE_MODE,None, True,False)
    if num_errors or num_warns:
        if Fix_Found_Problems:
            Auth_verified=False
            if len(overall_install_cmds) >0 and package_mgr_cmd:
                tui.header("Installation of Missing Packages")
                ok,user_input =tui.enter_choice("Update repository and Install missing/incompatible packages. (a=install all*, c=custom_install, s=skip, q=quit):",['a', 'c','s', 'q'], 'a')
                if not ok or user_input =='q':
                    log.info("User Exit")
                    sys.exit(0)
                elif user_input == 's':
                    log.info(log.bold("Install manually above missing/incompatible packages."))
                else:
                    if Auth_verified or check_permissions(core):
                        Auth_verified = True
                        close_package_managers(core)
                     
                    log.info(log.bold("Updating repository"))
                    log.info(log.bold('-'*len("Updating repository")))
                    if pre_depend_cmd:
                        for cmd in pre_depend_cmd:
                            log.info("cmd =%s"%(cmd))
                            sts, out = core.run(cmd)
                            if sts != 0  or "Failed" in out:
                                log.warn("Failed to update Repository, check if any update/installation is running.")
                         
                    if user_input =='c':
                        log.info(log.bold("Installing missing/incompatible packages"))
                        log.info(log.bold('-'*len("Installing missing/incompatible packages")))
                        for d in overall_install_cmds:
                            ok,user_input =tui.enter_choice("Do you want to install '%s' package?(y=yes*, n=no):"%d,['y', 'n'], 'y')
                            if ok and user_input == 'y':
                                if 'hpaio' in overall_install_cmds[d]:
                                    core.update_hpaio()
                                else:
                                    log.info("cmd =%s"%overall_install_cmds[d])
                                    sts, out = core.run(overall_install_cmds[d])    
                                    if sts != 0 or "Failed" in out:
                                        log.error("Failed to install '%s' package, please install manually. "%d)
                        if Is_cups_running is False:
                            if not start_service(core,'cups'):
                                log.error("Failed to start CUPS service. Please start CUPS manually or restart system.")

                    elif user_input =='a':
                        log.info(log.bold("Installing Missing/Incompatible packages"))
                        log.info(log.bold('-'*len("Installing Missing/Incompatible packages")))
                        for d in overall_install_cmds:
                            if 'hpaio' in overall_install_cmds[d]:
                                core.update_hpaio()
                            else:
                                log.info("cmd =%s"%overall_install_cmds[d])
                                sts, out = core.run(overall_install_cmds[d])
                                if sts != 0 or "Failed" in out:
                                    log.error("Failed to install '%s' package, please install manually. "%d)
                        if Is_cups_running is False:
                            if not start_service(core,'cups'):
                                log.error("Failed to start CUPS sevice. Please start CUPS manually or restart system.")

            elif len(overall_install_cmds) >0:
                log.info(log.bold("Please install above 'Missing Required Dependencies' and 'Missing Optional Dependencies'."))
                log.info()
            
           
            if plugin_error:
                ok,user_input =tui.enter_choice("Do you want to install missing/incompatible Plug-in's?(y=yes*, n=no)",['y', 'n'], 'y')
                if ok and user_input == 'y':
                    if Auth_verified or check_permissions(core):
                        Auth_verified = True
                        cmd = core.su_sudo() %'hp-plugin -i'
                        log.info("cmd = %s"%cmd)
                        os.system(cmd)

            if user_grp_error:
                if add_user_to_group:
                    ok,user_input =tui.enter_choice("Do you want to add missing groups to user?(y=yes*, n=no)",['y', 'n'], 'y')
                    if ok and user_input == 'y':
                        if Auth_verified or check_permissions(core):
                            Auth_verified = True
                            path= utils.which('usermod')
                            if path:
                                cmd = "%s/usermod %s %s" % (path,add_user_to_group, prop.username)
                                cmd = core.su_sudo()%cmd
                                log.info("cmd =  %s"%cmd)
                                core.run(cmd)
                                log.info(log.bold("\nNeed to reboot system to take effect of user group.\n"))
                            else:
                                log.error("usermod command not found.")
                else:
                    log.info(log.bold("Please add %s groups to %s user"%(add_user_to_group, prop.username)))
            if disable_selinux:
                ok,user_input =tui.enter_choice("SELinux is currently enabled in your system. Device may not work properly. Do you want to disable SELinux?(y=yes, n=no*)",['y', 'n'], 'n')
                if ok and user_input != 'n':
                    if Auth_verified or check_permissions(core):
                       Auth_verified = True
#                       cmd = "vi -c %s/SELINUX=enforcing/SELINUX=disabled -c wq /etc/selinux/config"
                       cmd = "vi -c %s/enforcing$/disabled -c wq /etc/selinux/config"
                       cmd=core.su_sudo()%cmd
                       log.debug("cmd= %s "%cmd)
                       core.run(cmd)
                       if os.path.exists('/selinux/enforce'):
                           cmd = "echo 0 >/selinux/enforce"
                           cmd=core.su_sudo()%cmd
                           log.debug("cmd= %s "%cmd)
                           core.run(cmd)
                       log.info(log.bold("\nNeed to reboot system to take effect.\n"))
        elif disable_selinux or user_grp_error or plugin_error or len(overall_install_cmds):
            log.info("Re-run 'hp-check --fix' command to prompt and fix the issues. ")

    else:
        log.info(log.green("No errors or warnings."))

except KeyboardInterrupt:
    log.error("User exit")

log.info()
log.info("Done.")
