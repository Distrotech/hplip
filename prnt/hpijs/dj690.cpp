/*****************************************************************************\
  dj690.cpp : Implimentation for the DJ6xxPhoto class

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


#ifdef APDK_DJ6xxPhoto

#include "header.h"
#include "dj690.h"
#include "printerproxy.h"

APDK_BEGIN_NAMESPACE

extern uint32_t ulMapDJ690_CMYK[ 9 * 9 * 9 ];
extern uint32_t ulMapDJ690_ClMlxx[ 9 * 9 * 9 ];
extern uint32_t ulMapDJ660_CCM_KCMY[ 9 * 9 * 9 ];
extern uint32_t ulMapDJ600_CCM_K[ 9 * 9 * 9 ];

//
// ** DJ6xxPhoto:Printer CLASS **
//
Mode690::Mode690()
// print mode for photo pen
: PrintMode( ulMapDJ690_CMYK, ulMapDJ690_ClMlxx )
{
   dyeCount=6;
   medium =  mediaSpecial;
   theQuality = qualityPresentation;
//   theQuality = qualityNormal;

   BaseResX = 600;
   for (int i=0; i < 6; i++)
        ResolutionX[i]=600;

   CompatiblePens[0] = MDL_BOTH;

//   strcpy(ModeName, "Photo");

   pmQuality = QUALITY_BEST;
   pmMediaType = MEDIA_PREMIUM;

}

GrayMode690::GrayMode690()
// print mode for photo pen
: PrintMode( ulMapDJ600_CCM_K )
{
   CompatiblePens[1] = MDL_BOTH;

   dyeCount = 1;

   pmColor=GREY_K;

}

#ifdef APDK_EXTENDED_MEDIASIZE
Mode690DraftColor::Mode690DraftColor()
: PrintMode( ulMapDJ660_CCM_KCMY )
{
    theQuality = qualityDraft;
    Config.eHT = MATRIX;
    pmQuality = QUALITY_DRAFT;
}

Mode690DraftGrayK::Mode690DraftGrayK()
: GrayMode(ulMapDJ600_CCM_K)
{
   theQuality = qualityDraft;
   pmQuality = QUALITY_DRAFT;
}

Mode690BestGrayK::Mode690BestGrayK()
: GrayMode(ulMapDJ600_CCM_K)
{
   theQuality = qualityPresentation;
   pmQuality = QUALITY_BEST;
   BaseResX = 600;
   ResolutionX[0] = 600;
#ifdef APDK_HIGH_RES_MODES
   BaseResY = 600;
   ResolutionY[0] = 600;
#else
   BaseResY = 300;
   ResolutionY[0] = 300;
#endif
}
#endif // APDK_EXTENDED_MEDIASIZE

DJ6xxPhoto::DJ6xxPhoto(SystemServices* pSS, BOOL proto)
    : Printer(pSS, NUM_DJ6XX_FONTS,proto)
// create two dummy font objects to be queried via EnumFont
{

    if ((!proto) && (IOMode.bDevID))
    {
        constructor_error = VerifyPenInfo();
        CERRCHECK;
    }
    else
    {
        ePen=BOTH_PENS;    // matches default mode
    }

    pMode[DEFAULTMODE_INDEX] = new PrintMode( ulMapDJ660_CCM_KCMY );    // normal color
    pMode[GRAYMODE_INDEX] = new GrayMode690();    // normal gray k
    pMode[SPECIALMODE_INDEX] = new Mode690();    // photo
#ifdef APDK_EXTENDED_MEDIASIZE
    pMode[SPECIALMODE_INDEX+1] = new Mode690DraftGrayK();
    pMode[SPECIALMODE_INDEX+2] = new Mode690DraftColor();
    pMode[SPECIALMODE_INDEX+3] = new Mode690BestGrayK();
    ModeCount=6;
#else
    ModeCount = 3;
#endif

    CMYMap = ulMapDJ660_CCM_KCMY;

    DBG1("DJ6xxPhoto created\n");

}


Header690::Header690(Printer* p,PrintContext* pc)
    : Header(p,pc)
{  }

Header* DJ6xxPhoto::SelectHeader(PrintContext* pc)
{
    return new Header690(this, pc);
}

DRIVER_ERROR Header690::Send()
{   DRIVER_ERROR err;

    StartSend();

    err = thePrinter->Send((const BYTE*)BlackExtractOff,
                        sizeof(BlackExtractOff)); // just pertains to 2-pen
    ERRCHECK;

    err = ConfigureRasterData();
    ERRCHECK;

    if (ResolutionY[0] == 600)
    {
        char uom[10];
        sprintf(uom,"%c%c%c%d%c",ESC,'&','u',thePrintMode->ResolutionY[K],'D');
        err=thePrinter->Send((const BYTE*)uom, 7 );
        ERRCHECK;
    }

    err=Graphics();     // start raster graphics and set compression mode

return err;
}
DRIVER_ERROR DJ6xxPhoto::VerifyPenInfo()
{

    DRIVER_ERROR err=NO_ERROR;

    if(IOMode.bDevID == FALSE)
        return err;

    err = ParsePenInfo(ePen);
    ERRCHECK;

    // check for the normal case
    if (ePen == BOTH_PENS || ePen == MDL_BOTH)
        return NO_ERROR;

DBG1("DJ6xxPhoto::VerifyPenInfo(): ePen is not BOTH_PENS or MDL_BOTH\n");

    // the 6XX printers are all two-pen, so trap
    // on any pen type that is not MDL_BOTH or
    // BOTH_PENS
    while ( (ePen != BOTH_PENS) && (ePen != MDL_BOTH)   )
    {
DBG1("DJ6xxPhoto::VerifyPenInfo(): in while loop\n");

        switch (ePen)
        {
            case MDL_PEN:
            case BLACK_PEN:
                // black or photopen installed, need to install color pen
                pSS->DisplayPrinterStatus(DISPLAY_NO_COLOR_PEN);
                break;
            case COLOR_PEN:
                // color pen installed, need to install black pen
                // - use ambiguous message because of black or photo pen
                pSS->DisplayPrinterStatus(DISPLAY_NO_PEN_DJ600);
                break;
            case NO_PEN:
                // neither pen installed
            default:
                pSS->DisplayPrinterStatus(DISPLAY_NO_PENS);
                break;
        }

        if (pSS->BusyWait(500) == JOB_CANCELED)
            return JOB_CANCELED;

        err =  ParsePenInfo(ePen);
        ERRCHECK;
    }

    pSS->DisplayPrinterStatus(DISPLAY_PRINTING);

    return NO_ERROR;

}

DRIVER_ERROR DJ6xxPhoto::ParsePenInfo(PEN_TYPE& ePen, BOOL QueryPrinter)
{
    char* str;
    DRIVER_ERROR err = SetPenInfo(str, QueryPrinter);
    ERRCHECK;

    if (*str != '$')
    {
        return BAD_DEVICE_ID;
    }

    str++;    // skip $
    // parse penID
    PEN_TYPE temp_pen1;
    // check pen1, assume it is black or MDL, pen2 is color
    switch (str[0])
    {
        // check for MDL in case someone wedged one in there
        case 'M': temp_pen1 = MDL_PEN; break; // (M)ulti-Dye load pen
        case 'C': temp_pen1 = BLACK_PEN; break; // (C)andide black
        default:  temp_pen1 = NO_PEN; break;
    }

    // now check pen2

    int i=2;
    while((i < DevIDBuffSize) && str[i]!='$') i++; // handles variable length penIDs
    if (i == DevIDBuffSize)
    {
        return BAD_DEVICE_ID;
    }

    i++;

    if(str[i]=='R') // we have the (R)obinhood color pen,
                    // check what pen1 was
    {
        if (temp_pen1 == BLACK_PEN)
                ePen = BOTH_PENS;
        else
        {
            if (temp_pen1 == MDL_PEN)
                ePen = MDL_BOTH;
            else
                ePen = COLOR_PEN;
        }
    }
    else // no color pen, just set what pen1 was
        ePen = temp_pen1;

    return NO_ERROR;
}

APDK_END_NAMESPACE

#endif  //APDK_DJ690
