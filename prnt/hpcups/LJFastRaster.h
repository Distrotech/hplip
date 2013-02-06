/*****************************************************************************\
  LJFastRaster.h : Interface for LJFastRaster class

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

#ifndef LJFASTRASTER_H
#define LJFASTRASTER_H

#include "CommonDefinitions.h"
#include "Pipeline.h"
#include "Encapsulator.h"
#include "ModeDeltaPlus.h"

class Halftoner;

class LJFastRaster: public Encapsulator
{
public:
    LJFastRaster();
    ~LJFastRaster();
    DRIVER_ERROR    Encapsulate (RASTERDATA *InputRaster, bool bLastPlane);
    DRIVER_ERROR    StartPage(JobAttributes *pJA);
    DRIVER_ERROR    Configure(Pipeline **pipeline);
	DRIVER_ERROR    EndJob();
	DRIVER_ERROR    FormFeed();
	DRIVER_ERROR    SendCAPy(int iOffset);
	bool            CanSkipRasters() {return false;}
	void            CancelJob() {}
	void            SetLastBand() 
	{
	    m_pModeDeltaPlus->SetLastBand();
	}
protected:
    virtual DRIVER_ERROR addJobSettings();
    DRIVER_ERROR flushPrinterBuffer() {return NO_ERROR;}
private:
    PrintMode    m_PM;
	ModeDeltaPlus    *m_pModeDeltaPlus;
};

#endif // LJFASTRASTER_H

