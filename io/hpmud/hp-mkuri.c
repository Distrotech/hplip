/*****************************************************************************\

  hp-mkuri.c - make uri with multi-point transport driver (HPMUD)
 
  (c) 2008-2009 Copyright Hewlett-Packard Development Company, LP

  Permission is hereby granted, free of charge, to any person obtaining a copy 
  of this software and associated documentation files (the "Software"), to deal 
  in the Software without restriction, including without limitation the rights 
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies 
  of the Software, and to permit persons to whom the Software is furnished to do 
  so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS 
  FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR 
  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
  IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
  WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

\*****************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <signal.h>
#include <ctype.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <syslog.h>
#include <dlfcn.h>
#include "hpmud.h"

#define _STRINGIZE(x) #x
#define STRINGIZE(x) _STRINGIZE(x)
//#define BUG(args...) fprintf(stderr, __FILE__ " " STRINGIZE(__LINE__) ": " args)
#define BUG(args...) syslog(LOG_ERR, __FILE__ " " STRINGIZE(__LINE__) ": " args)

static int verbose;
static char homedir[255] = "";

static void usage()
{
   fprintf(stdout, "HPLIP Make URI %s\n", VERSION);
   fprintf(stdout, "(c) 2008 Copyright Hewlett-Packard Development Company, LP\n");
   fprintf(stdout, "usage: hp-mkuri -i ip [-p port]\n");
   fprintf(stdout, "usage: hp-mkuri -z hostname\n");
   fprintf(stdout, "usage: hp-mkuri -b busnum -d devnum\n");
   fprintf(stdout, "usage: hp-mkuri -s serialnum\n");
   fprintf(stdout, "usage: hp-mkuri -l /dev/parportx\n");
   fprintf(stdout, "usage: hp-mkuri -m hostname [-p port]\n");
   fprintf(stdout, "usage: hp-mkuri -o (probe)\n");
   fprintf(stdout, "usage: hp-mkuri -c [-n (no notifier)] (check support)\n");
   fprintf(stdout, "\nSupport matrix:\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "| return value | printer | fax | plugin_required | plugin_optional |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       0      |   yes   |     |                 |                 |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       1      |    *    |  *  |        *        |        *        |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       2      |   yes   |     |       yes       |                 |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       3      |   yes   |     |                 |       yes       |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       4      |   yes   | yes |                 |                 |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       5      |   yes   | yes |       yes       |                 |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "|       6      |   yes   | yes |                 |       yes       |\n");
   fprintf(stdout, "+--------------+---------+-----+-----------------+-----------------+\n");
   fprintf(stdout, "    * no support or error\n");
} /* usage */

static int GetPair(char *buf, int buf_len, char *key, char *value, char **tail)
{
   int i=0, j;

   key[0] = 0;
   value[0] = 0;

   if (buf[i] == '#')
   {
      for (; buf[i] != '\n' && i < buf_len; i++);  /* eat comment line */
      if (buf[i] == '\n')
         i++;   /* bump past '\n' */
   }

   j = 0;
   while ((buf[i] != '=') && (i < buf_len) && (j < HPMUD_LINE_SIZE))
      key[j++] = buf[i++];
   for (j--; key[j] == ' ' && j > 0; j--);  /* eat white space before = */
   key[++j] = 0;

   if (buf[i] == '=')
      for (i++; buf[i] == ' ' && i < buf_len; i++);  /* eat white space after = */

   j = 0;
   while ((buf[i] != '\n') && (i < buf_len) && (j < HPMUD_LINE_SIZE))
      value[j++] = buf[i++];
   for (j--; value[j] == ' ' && j > 0; j--);  /* eat white space before \n */
   value[++j] = 0;

   if (buf[i] == '\n')
     i++;   /* bump past '\n' */

   if (tail != NULL)
      *tail = buf + i;  /* tail points to next line */

   return i;
}

static int ReadConfig()
{
   char key[HPMUD_LINE_SIZE];
   char value[HPMUD_LINE_SIZE];
   char rcbuf[255];
   char section[32];
   char *tail;
   FILE *inFile = NULL;
   int stat=1;

   homedir[0] = 0;
        
   if((inFile = fopen(CONFDIR "/hplip.conf", "r")) == NULL) 
   {
      BUG("unable to open %s: %m\n", CONFDIR "/hplip.conf");
      goto bugout;
   } 

   section[0] = 0;

   /* Read the config file */
   while ((fgets(rcbuf, sizeof(rcbuf), inFile) != NULL))
   {
      if (rcbuf[0] == '[')
      {
         strncpy(section, rcbuf, sizeof(section)); /* found new section */
         continue;
      }

      GetPair(rcbuf, strlen(rcbuf), key, value, &tail);

      if ((strncasecmp(section, "[dirs]", 6) == 0) && (strcasecmp(key, "home") == 0))
      {
         strncpy(homedir, value, sizeof(homedir));
         break;  /* done */
      }
   }
        
   stat = 0;

bugout:        
   if (inFile != NULL)
      fclose(inFile);
         
   return stat;
}

static int generalize_model(const char *sz, char *buf, int bufSize)
{
   const char *pMd=sz;
   int i, j, dd=0;

   for (i=0; pMd[i] == ' ' && i < bufSize; i++);  /* eat leading white space */

   for (j=0; (pMd[i] != 0) && (pMd[i] != ';') && (j < bufSize); i++)
   {
      if (pMd[i]==' ' || pMd[i]=='/')
      {
         /* Remove double spaces. */
         if (!dd)
         { 
            buf[j++] = '_';   /* convert space to "_" */
            dd=1;              
         }
      }
      else
      {
         buf[j++] = tolower(pMd[i]);
         dd=0;       
      }
   }

   for (j--; buf[j] == '_' && j > 0; j--);  /* eat trailing white space */

   buf[++j] = 0;

   return j;   /* length does not include zero termination */
}

static int set_x_environment(void)
{
   DIR *dir=NULL;
   FILE *file=NULL;
   struct dirent *entry;
   char path[32], line[256], cookie[128], *p;
   int i, c, stat=1;

   if ((dir = opendir("/proc"))==NULL)
   {
      BUG("unable to open /proc: %m\n");
      goto bugout;
   }

   while ((entry = readdir(dir)) != NULL) 
   {
      if (!isdigit(*entry->d_name))
         continue;

      /* Get command line for this PID. */
      snprintf(path, sizeof(path), "/proc/%s/cmdline", entry->d_name);
      if ((file = fopen(path, "r")) == NULL)
         continue;
      for (i=0; ((c = getc(file)) != EOF) && (i < (sizeof(line)-1)); i++)
      {
         if (c == 0)
            c = ' ';
         line[i] = c;
      }
      line[i]=0;
      fclose(file);
      if ((p = strstr(line, "-auth ")))
      {
         /* Found X server. */
         for (p+=6; (*p == ' ') && (*p != 0); p++);  /* eat any white space before cookie */
         for (i=0; (*(p+i) != ' ') && (*(p+i) != 0) && i < (sizeof(cookie)-1); i++)
            cookie[i] = *(p+i);
         cookie[i]=0;
         setenv("XAUTHORITY", cookie, 1);
         setenv("DISPLAY", ":0.0", 1);
         break; 
      }
   } /* while ((entry = readdir(dir)) != NULL) */ 

   stat = 0;

bugout:
   if (dir)
      closedir(dir);
   return(stat);
}  /* set_x_environment */

static int notify(const char *summary, const char *message, int ms_timeout) 
{
    void *handle=NULL, *n;
    int stat=1; 

    typedef void  (*notify_init_t)(char *);
    typedef void *(*notify_notification_new_t)(const char *, const char *, const char *, void *);
    typedef void  (*notify_notification_set_timeout_t)(void *, int);
    typedef void (*notify_notification_show_t)(void *, char *);

    notify_init_t n_init;
    notify_notification_new_t n_new;
    notify_notification_set_timeout_t n_timeout;
    notify_notification_show_t n_show;

    set_x_environment();

    /* Bypass glib build dependencies by loading libnotify manually. */  

    if ((handle = dlopen("libnotify.so.1", RTLD_LAZY)) == NULL)
    {
       BUG("failed to open libnotify: %m\n");
       goto bugout;
    }

    if ((n_init = (notify_init_t)dlsym(handle, "notify_init")) == NULL)
    {
       BUG("failed to find notify_init: %m\n");
       goto bugout; 
    }
    n_init("Basics");

    if ((n_new = (notify_notification_new_t)dlsym(handle, "notify_notification_new")) == NULL)
    {
       BUG("failed to find notify_notification_new: %m\n");
       goto bugout;
    }
    n = n_new(summary, message, NULL, NULL);

    if ((n_timeout = (notify_notification_set_timeout_t)dlsym(handle, "notify_notification_set_timeout")) == NULL)
    {
        BUG("failed to find notify_notification_set_timeout: %m\n");
        goto bugout;
    }
    n_timeout(n, ms_timeout);

    if ((n_show = (notify_notification_show_t)dlsym(handle, "notify_notification_show")) == NULL)
    {
       BUG("failed to find notify_notification_show: %m\n");
       goto bugout;
    }
    n_show(n, NULL);

    stat=0;

bugout:
    if (handle)
       dlclose(handle);

    return stat;
} /* notify */

static int check_support(int send_notify)
{
   struct stat sb;
   char model[256];
   int ret=1, plugin_installed=1;
   const char *pm;
   char m[256];
   char datfile[256];
   char value[32];
   int support, plugin, fax;

   /* Get hp model from environment variables. */
   if ((pm = getenv("hp_model")))
   {
      strncpy(model, pm, sizeof(model));
   }
   else
   {
      fprintf(stderr, "error no hp_model environment variable set\n");
      BUG("error no hp_model environment variable set\n");
      goto bugout;
   }

   if (model[0]==0)
   {
      BUG("invalid parameter(s)\n");
      usage();
      goto bugout;
   } 

   generalize_model(model, m, sizeof(m));
   snprintf(model, sizeof(model), "[%s]", m);

   if (ReadConfig())
      goto bugout;

   snprintf(datfile, sizeof(datfile), "%s/data/models/models.dat", homedir);

   if (hpmud_get_key_value(datfile, model, "support-type", value, sizeof(value)) != HPMUD_R_OK)
      goto bugout;
   support = strtol(value, NULL, 10);
   if (hpmud_get_key_value(datfile, model, "plugin", value, sizeof(value)) != HPMUD_R_OK)
      goto bugout;
   plugin = strtol(value, NULL, 10);
   if (hpmud_get_key_value(datfile, model, "fax-type", value, sizeof(value)) != HPMUD_R_OK)
      goto bugout;
   fax = strtol(value, NULL, 10);

   /* See if device is supported by hplip. */
   if (support == HPMUD_SUPPORT_TYPE_NONE)
   {
      BUG("%s is not supported by HPLIP %s\n", pm, VERSION);
      goto bugout;
   }

   if (stat("/etc/udev/rules.d/86-hpmud-hp_laserjet_1018.rules", &sb) == -1) 
      plugin_installed=0;

   if (send_notify && !plugin_installed)
   {
      /* See if device requires a Plugin. */
      switch (plugin)
      {
         case HPMUD_PLUGIN_TYPE_REQUIRED:
            BUG("%s requires a proprietary plugin\n", pm);
            notify(pm, "requires a proprietary plugin, run hp-setup", 30000);
            break;
         case HPMUD_PLUGIN_TYPE_OPTIONAL:
            BUG("%s has a optional proprietary plugin\n", pm);
            notify(pm, "has a optional proprietary plugin, run hp-setup", 30000);
            break;
         default:
            break;
      }         
   }

   ret = 0;
   if (plugin == HPMUD_PLUGIN_TYPE_REQUIRED)
      ret = 2;
   else if (plugin == HPMUD_PLUGIN_TYPE_OPTIONAL)
      ret = 3;
   if (fax > 0)
   {
      ret = 4;
      if (plugin == HPMUD_PLUGIN_TYPE_REQUIRED)
         ret = 5;
      else if (plugin == HPMUD_PLUGIN_TYPE_OPTIONAL)
         ret = 6;
   }

bugout:
   return ret;
} /* check_support */

int main(int argc, char *argv[])
{
   char ip[HPMUD_LINE_SIZE];  /* internet address */
   char bn[HPMUD_LINE_SIZE];  /* usb bus number */
   char dn[HPMUD_LINE_SIZE];  /* usb device number */
   char sn[HPMUD_LINE_SIZE];  /* usb serial number */
   char pp[HPMUD_LINE_SIZE];  /* parallel port device */
   char uri[HPMUD_LINE_SIZE];
   char host[HPMUD_LINE_SIZE];
   int i, port=1, ret=1, probe=0, support=0, send_notify=1;
   enum HPMUD_RESULT stat;
   char buf[HPMUD_LINE_SIZE*64];
   int cnt, bytes_read;

   ip[0] = bn[0] = dn[0] = pp[0] = uri[0] = sn[0] = host[0] = 0;
   while ((i = getopt(argc, argv, "vhocni:p:b:d:l:s:z:")) != -1)
   {
      switch (i)
      {
      case 'i':
         strncpy(ip, optarg, sizeof(ip));
         break;
      case 'z':
         strncpy(host, optarg, sizeof(host));
         break;
      case 'p':
         port = strtol(optarg, NULL, 10);
         break;
      case 'b':
         strncpy(bn, optarg, sizeof(bn));
         break;
      case 'd':
         strncpy(dn, optarg, sizeof(dn));
         break;
      case 'l':
         strncpy(pp, optarg, sizeof(pp));
         break;
      case 's':
         strncpy(sn, optarg, sizeof(sn));
         break;
      case 'o':
         probe++;
         break;
      case 'c':
         support++;
         break;
      case 'v':
         verbose++;
         break;
      case 'n':
         send_notify=0;
         break;
      case 'h':
         usage();
         exit(0);
      case '?':
         usage();
         fprintf(stderr, "unknown argument: %s\n", argv[1]);
         exit(-1);
      default:
         break;
      }
   }

   if (ip[0]==0 && (!(bn[0] && dn[0])) && pp[0]==0 && probe==0 && sn[0]==0 && support==0 && host[0]==0)
   {
      fprintf(stderr, "invalid command parameter(s)\n");
      usage();
      goto bugout;
   }   

   if (probe)
   {
      hpmud_probe_devices(HPMUD_BUS_ALL, buf, sizeof(buf), &cnt, &bytes_read);
      if (bytes_read)
         fprintf(stdout, "%s", buf);
   }

#ifdef HAVE_LIBNETSNMP
   if (ip[0])
   {
      stat = hpmud_make_net_uri(ip, port, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }
   if (host[0])
   {
      stat = hpmud_make_mdns_uri(host, port, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }
#endif

   if (bn[0] && dn[0])
   {
      stat = hpmud_make_usb_uri(bn, dn, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }

   if (sn[0])
   {
      stat = hpmud_make_usb_serial_uri(sn, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }

#ifdef HAVE_PPORT
   if (pp[0])
   {
      stat = hpmud_make_par_uri(pp, uri, sizeof(uri), &bytes_read);
      if (stat == HPMUD_R_OK)
      {
         fprintf(stdout, "%s\n", uri);
         fprintf(stdout, "hpaio%s\n", &uri[2]);
      }
   }
#endif

   ret = 0;

   if (support)
      ret = check_support(send_notify);

bugout:
   exit(ret);
} /* main */
