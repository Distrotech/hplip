/*****************************************************************************\
    hplipjs.c : HP Job Storage Pin Printing filter for PostScript printers

    Copyright (c) 2012, Hewlett-Packard Co.
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions
    are met:
    1. Redistributions of source code must retain the above copyright
       notice, this list of conditions and the following disclaimer.
    2. Redistributions in binary form must reproduce the above copyright
       notice, this list of conditions and the following disclaimer in the
       documentation and/or other materials provided with the distribution.
    3. Neither the name of the Hewlett-Packard nor the names of its
       contributors may be used to endorse or promote products derived
       from this software without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
    OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
    IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
    INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
    NOT LIMITED TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
    IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

    AUTHOR: GAURAV SOOD
\*****************************************************************************/

#include <stdio.h>
#include <string.h>
#include <memory.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <cups/cups.h>
#include <sys/types.h>
#include <pwd.h>


#ifdef TESTING
FILE    *HPFp;
int HPWrite (int fd, void *pBuffer, int len)
{
    fwrite (pBuffer, 1, len, HPFp);
    return len;
}
#else
#define HPWrite write
#endif

static char    *szJSStrings[] = {"HOLDKEY", "USERNAME", "JOBNAME", "HOLDTYPE", "DUPLICATEJOB"};

void SendJobHoldCommands (char *szJSOptions, int fd)
{
    int     i, k;
    int     iJS;
    char    *p;
    char    szStr[256];
    p = strstr (szJSOptions, "HOLD");
    if (!(strncmp (p+5, "OFF", 3)))
        return;
    while (*p && *p != '=')
        p++;
    p++;
    k = 14;
    memset (szStr, 0, sizeof (szStr));
    strcpy (szStr, "@PJL SET HOLD=");
    while (*p && *p > ' ' && k < 254)
    {
        szStr[k++] = *p++;
    }
    szStr[k] = '\x0A';
    HPWrite (fd, szStr, strlen (szStr));

    p = szJSOptions;
    iJS = sizeof (szJSStrings) / sizeof (szJSStrings[0]);
    for (i = 0; i < iJS; i++)
    {
	    if ((p = strstr (szJSOptions, szJSStrings[i])))
	    {
	        memset (szStr, 0, sizeof (szStr));
	        sprintf (szStr, "@PJL SET %s=", szJSStrings[i]);
	        while (*p && *p != '=')
		        p++;
	        p++;
	        k = strlen (szStr);
	        if (i < 3)
		    szStr[k++] = '"';
	        while (*p && *p > ' ' && k < 254)
	        {
		        szStr[k] = *p++;
		        if (szStr[k] == '_')
		            szStr[k] = ' ';
		        k++;
	        }
	        if (i < 3)
		    szStr[k++] = '"';
	        szStr[k] = '\x0A';
	        HPWrite (fd, szStr, strlen (szStr));
	    }
    }
    return;
}

void GetOptionStringFromCups (char *pPrinter, int fd, char *user)
{
    struct    passwd    *pwd;
    char      szlpOptionsFile[1024];
    FILE      *fp;
    char      szLine[1024];
    pwd = getpwnam (user);
    if (pwd == NULL)
    {
        fprintf (stderr, "DEBUG: getpwnam failed for user %s\n", user);
        return;
    }
    sprintf (szlpOptionsFile, "%s/.cups/lpoptions", pwd->pw_dir);
    fp = fopen (szlpOptionsFile, "r");
    if (fp == NULL)
    {
        fprintf (stderr, "DEBUG: Unable to open lpoptions file %s\n", szlpOptionsFile);
        return;
    }
    while (!feof (fp))
    {
        fgets (szLine, 1020, fp);
        if (strstr (szLine, pPrinter))
        {
            fprintf (stderr, "DEBUG: Got %s from lpoptions file\n", szLine);
            SendJobHoldCommands (szLine + strlen (pPrinter) + 5, fd);
            break;
        }
    }
    fclose (fp);
}

#if 0
void GetOptionStringFromCups (char *pPrinter, int fd)
{
    int            i, j;
    int            iJS;
    int            num_dests;
    cups_dest_t    *dests;
    cups_dest_t    *dest;
    char           *opt;
    char           *ppdFileName;
    ppd_file_t     *ppdFile;
    char           szJSOptionString[1024];

fprintf (stderr, "DEBUG: In GetOption.... printer = %s, fd = %d\n", pPrinter, fd);
    ppdFileName = (char *) cupsGetPPD (pPrinter);
    if (!ppdFileName)
    {
fprintf (stderr, "DEBUG: did not get ppdfilename\n");
        return;
    }
fprintf (stderr, "DEBUG: ppdFileName = %s\n", ppdFileName);
    ppdFile = ppdOpenFile (ppdFileName);
fprintf (stderr, "DEBUG: ppdFileName = %s\n", ppdFileName);
    if (ppdFile == NULL)
    {
fprintf (stderr, "DEBUG: unable to open ppdfile, %s\n", ppdFileName);
        return;
    }
    num_dests = cupsGetDests (&dests);
    if (num_dests == 0)
    {
fprintf (stderr, "DEBUG: num_dests is zero\n");
        ppdClose (ppdFile);
        return;
    }
    dest = cupsGetDest (pPrinter, NULL, num_dests, dests);
    if (dest == NULL)
    {
fprintf (stderr, "DEBUG: did not get dest for printer %s\n", pPrinter);
        ppdClose (ppdFile);
        return;
    }
    ppdMarkDefaults (ppdFile);
    cupsMarkOptions (ppdFile, dest->num_options, dest->options);
    iJS = sizeof (szJSStrings) / sizeof (szJSStrings[0]);
    if ((opt = (char *) cupsGetOption ("HOLD", dest->num_options, dest->options)) == NULL)
    {
fprintf (stderr, "DEBUG: did not see HOLD option\nOptions in the list are:\n");
for (i = 0; i < dest->num_options; i++)
{
    fprintf (stderr, "DEBUG: Option = %s : value = %s\n", dest->options[i].name, dest->options[i].value);
}

        ppdClose (ppdFile);
        return;
    }
    memset (szJSOptionString, 0, sizeof (szJSOptionString));
    j = sprintf (szJSOptionString, "HOLD=%s", opt);
    for (i = 0; i < iJS; i++)
    {
        if ((opt = (char *) cupsGetOption (szJSStrings[i], dest->num_options, dest->options)))
        {
fprintf (stderr, "DEBUG: cupsGetOption returned %s = %s\n", szJSStrings[i], opt);
            j += sprintf (szJSOptionString + j, " %s=%s", szJSStrings[i], opt);
        }
    }
    ppdClose (ppdFile);
    cupsFreeDests (num_dests, dests);
fprintf (stderr, "DEBUG: Calling SendJobHoldCommands with %s\n", szJSOptionString);
    SendJobHoldCommands (szJSOptionString, fd);
}
#endif

char secpin[5];
char* foo(char *szOptions)
{
	char szKeyInitials[][10] = {"HPFIDigit", "HPSEDigit", "HPTHDigit", "HPFTDigit"};
	int i;

	//char secpin[4];

	for (i = 0; i <= 3; i++)
		if (!(strstr(szOptions, szKeyInitials[i])))
			secpin[i] = 48;
		else 
		secpin[i] = szOptions[strstr(szOptions, szKeyInitials[i]) - szOptions + 10];
	secpin[i] = '\0';
	return secpin;
}

int main (int argc, char **argv)
{
#ifdef TESTING
    int    i;
#endif
    int    n;
    int    fd;
    int    Outfd;
    char   pBuffer[260];
    char   *szStartJob = "\x1B%-12345X@PJL JOBNAME=";
    char   *szUEL = "@PJL ENTER LANGUAGE=POSTSCRIPT\x0A";
    char   *szEndJob = "\x1B%-12345X@PJL EOJ\x0A\x1B%-12345X";
    char   *szUserName = "@PJL SET USERNAME=";
    char   *szJobName = "@PJL SET JOBNAME=";
    char   *szNumCopies = "@PJL SET COPIES=";
    char   *szHold = "@PJL SET HOLD=ON\x0A";
    char   *szType = "@PJL SET HOLDTYPE=PRIVATE\x0A";
    char   *szKey = "@PJL SET HOLDKEY=";
    char   szPSFile[64];
/*
 *  Job storage command strings
 *
 *  @PJL SET HOLD=ON | OFF | STORE | REPRINT
 *                hold in memory, regular job, store to hdd, reprint from memory
 *  @PJL SET HOLDTYPE=PRIVATE | PUBLIC
 *  @PJL SET HOLDKEY=1234
 *  @PJL SET USERNAME="user_name"
 *  @PJL SET JOBNAME="job_name"
 *  @PJL SET DUPLICATEJOB=APPEND | REPLACE
 */

    setbuf (stderr, NULL);
    if (argc < 6 || argc > 7)
    {
        fprintf (stderr, "ERROR: Uage - %s JobId UserName Title NCopies OptionList [InputFile]\n", *argv);
        return 1;
    }

//  Doesn't really work
//    cupsSetUser (argv[2]);

#ifdef TESTING
    for (i = 0; i < argc; i++)
    {
        fprintf (stderr, "DEBUG: HPLIPJS: argv[%d] = %s\n", i, argv[i]);
    }
    snprintf(szPSFile, sizeof(szPSFile), "%s/output.ps","/var/log/hp/tmp");

    HPFp = fopen (szPSFile, "w");
#endif
    fd = 0;        // read from stdin
    Outfd = 1;     // HPWrite to stdout
    if (argc == 7)
    {
        if ((fd = open (argv[6], O_RDONLY)) == -1)
        {
            fprintf (stderr, "ERROR: Unable to open input file %s for reading\n", argv[6]);
            return 1;
        }
    }

    HPWrite (Outfd, szStartJob, strlen (szStartJob));
    sprintf (pBuffer, "hplip-%s\x0A", argv[1]);
    HPWrite (Outfd, pBuffer, strlen (pBuffer));

/*
 *  Check if job storage option is selected. If so, send the PJL header and
 *  job storage commands.
 */

   

if  (( strstr(argv[5], "HPPin")) &&  !(strstr (argv[5], "noHPPinPrnt")))
    {
        fprintf (stderr, "DEBUG: found HOLD option\n");
	HPWrite (Outfd, szHold, strlen (szHold));
	HPWrite (Outfd, szType, strlen (szType));
	//pin = foo(argv[5]);
        //SendJobHoldCommands (argv[5], Outfd);
	HPWrite (Outfd, szKey, strlen(szKey));
	sprintf (pBuffer, "\"%s\"\x0A", foo(argv[5]));
	HPWrite (Outfd, pBuffer, strlen (pBuffer));

	HPWrite (Outfd, szUserName, strlen(szUserName));
	sprintf (pBuffer, "\"%s\"\x0A", argv[2]);
	HPWrite (Outfd, pBuffer, strlen (pBuffer));

	HPWrite (Outfd, szJobName, strlen(szJobName));
	sprintf (pBuffer, "\"%s\"\x0A", argv[3]);
	HPWrite (Outfd, pBuffer, strlen (pBuffer));

	HPWrite (Outfd, szNumCopies, strlen(szNumCopies));
	sprintf (pBuffer, "%s\x0A", argv[4]);
	HPWrite (Outfd, pBuffer, strlen (pBuffer));
	
    }
    else
    {
        fprintf (stderr, "DEBUG: did not find HOLD option, calling GetOption....\n");
        GetOptionStringFromCups (argv[0], Outfd, argv[2]);
    }

    HPWrite (Outfd, szUEL, strlen (szUEL));

    while ((n = read (fd, pBuffer, 256)) > 0)
    {
        HPWrite (Outfd, pBuffer, n);
    }

    HPWrite (Outfd, szEndJob, strlen (szEndJob));

    if (fd != 0)
        close (fd);
#ifdef TESTING
    fclose (HPFp);
#endif
    return 0;
}
