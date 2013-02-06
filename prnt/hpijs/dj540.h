/*****************************************************************************\
  dj540.h : Interface for the DJ540 class

  Copyright (c) 1996 - 2001, Hewlett-Packard Co.
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


#ifndef APDK_DJ540_H
#define APDK_DJ540_H

APDK_BEGIN_NAMESPACE

/*!
\internal
*/
class DJ540 : public DJ6XX
{
public:
    DJ540(SystemServices* pSS, BOOL proto=FALSE);

    Header* SelectHeader(PrintContext* pc);
    DRIVER_ERROR VerifyPenInfo();
    virtual DRIVER_ERROR ParsePenInfo(PEN_TYPE& ePen, BOOL QueryPrinter=TRUE);
    virtual PEN_TYPE DefaultPenSet();

}; //DJ540

#ifdef APDK_DJ540
//! DJ540Proxy
/*!
******************************************************************************/
class DJ540Proxy : public PrinterProxy
{
public:
    DJ540Proxy() : PrinterProxy(
        "DJ540",                    // family name
        "DESKJET 540\0"                         // DeskJet 540
#ifdef APDK_MLC_PRINTER
        "OfficeJet Series 3\0"                  // OfficeJet Series 300
#endif
    ) {m_iPrinterType = eDJ540;}
    inline Printer* CreatePrinter(SystemServices* pSS) const { return new DJ540(pSS); }
	inline PRINTER_TYPE GetPrinterType() const { return eDJ540;}
	inline unsigned int GetModelBit() const { return 0x400000;}
};
#endif

APDK_END_NAMESPACE

#endif //APDK_DJ540_H
