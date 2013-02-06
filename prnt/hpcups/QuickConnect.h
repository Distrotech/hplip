/*****************************************************************************\
  QuickConnect.h : Interface for Pcl3Gui2 class

  Copyright (c) 1996 - 2009, Hewlett-Packard Co.
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:
  1. Redistributions of source code must retain the above copyright
     notice, this list of conditions and the following disclaimer.
  2. Redistributions in binary form must reproduce the above copyright
     notice, this list of conditions and the following disclaimer in the
     documentation and/or other materials provided with the distribution.
  3. Neither the name of Hewlett-Packard nor the names of its
     contributors may be used to endorse or promote products derived
     from this software without specific prior written permission.

  THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR IMPLIED
  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
  NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
  TO, PATENT INFRINGEMENT; PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
  OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
\*****************************************************************************/

#ifndef QUICK_CONNECT_H
#define QUICK_CONNECT_H

class QuickConnect: public Encapsulator
{
public:
    QuickConnect();
	~QuickConnect();
	DRIVER_ERROR    Encapsulate(RASTERDATA *InputRaster, bool bLastPlane);
    DRIVER_ERROR    StartJob(SystemServices *pSystemServices, JobAttributes *pJA);
	DRIVER_ERROR    StartPage(JobAttributes *pJA);
	DRIVER_ERROR    Configure(Pipeline **pipeline);
	DRIVER_ERROR    SendCAPy(int iOffset) {return NO_ERROR;}
	DRIVER_ERROR    FormFeed() {return NO_ERROR;}
	DRIVER_ERROR    EndJob() {return NO_ERROR;}
	DRIVER_ERROR    Cleanup() {return NO_ERROR;}
	bool            CanSkipRasters() {return false;}
protected:
    bool needPJLHeaders(JobAttributes *pJA)
    {
        return false;
    }
    DRIVER_ERROR        addJobSettings() {return NO_ERROR;}
    DRIVER_ERROR    flushPrinterBuffer() {return NO_ERROR;}
private:
    DRIVER_ERROR    sendExifHeader(BYTE *jpeg_data, int *header_size);
};

#endif // QUICK_CONNECT_H

