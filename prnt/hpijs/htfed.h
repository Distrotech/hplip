/*****************************************************************************\
  hfed.h : Open Source Imaging error diffusion prototypes

  Copyright (c) 1994 - 2001, Hewlett-Packard Co.
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


#ifndef HTFED_H
#define HTFED_H

#define FORWARD_FED( thresholdValue, bitMask )\
{\
    tone = (*inputPtr++ );\
    fedResPtr = fedResTbl + (tone << 2);\
    level = *fedResPtr++;\
    if (tone != 0)\
    {\
    tone = ( tmpShortStore + (HPInt16)(*fedResPtr++) );\
    if (tone >= thresholdValue)\
        {\
        tone -= 255;\
        level++;\
        }\
        switch (level)\
        {\
            case 0:\
            break;\
            case 1:\
            rasterByte1 |= bitMask;\
            break;\
            case 2:\
            rasterByte2 |= bitMask;\
            break;\
            case 3:\
            rasterByte2 |= bitMask; rasterByte1 |= bitMask;\
            break;\
            case 4:\
            rasterByte3 |= bitMask;\
            break;\
            case 5:\
            rasterByte3 |= bitMask; rasterByte1 |= bitMask;\
            break;\
            case 6:\
            rasterByte3 |= bitMask; rasterByte2 |= bitMask;\
            break;\
            case 7:\
            rasterByte3 |= bitMask; rasterByte2 |= bitMask; rasterByte1 |= bitMask;\
            break;\
        }\
    }\
    else\
    {\
    tone = tmpShortStore;\
    }\
    *diffusionErrorPtr++ = tone >> 1;\
    tmpShortStore = *diffusionErrorPtr + (tone - (tone >> 1));\
}

#define BACKWARD_FED( thresholdValue, bitMask )\
{\
    tone = (*inputPtr-- );\
    fedResPtr = fedResTbl + (tone << 2);\
    level = *fedResPtr++;\
    if (tone != 0)\
    {\
    tone = ( tmpShortStore + (HPInt16)(*fedResPtr++) );\
    if (tone >= thresholdValue)\
        {\
        tone -= 255;\
        level++;\
        }\
        switch (level)\
        {\
            case 0:\
            break;\
            case 1:\
            rasterByte1 |= bitMask;\
            break;\
            case 2:\
            rasterByte2 |= bitMask;\
            break;\
            case 3:\
            rasterByte2 |= bitMask; rasterByte1 |= bitMask;\
            break;\
            case 4:\
            rasterByte3 |= bitMask;\
            break;\
            case 5:\
            rasterByte3 |= bitMask; rasterByte1 |= bitMask;\
            break;\
            case 6:\
            rasterByte3 |= bitMask; rasterByte2 |= bitMask;\
            break;\
            case 7:\
            rasterByte3 |= bitMask; rasterByte2 |= bitMask; rasterByte1 |= bitMask;\
            break;\
        }\
    }\
    else\
    {\
    tone = tmpShortStore;\
    }\
    *diffusionErrorPtr-- = tone >> 1;\
    tmpShortStore = *diffusionErrorPtr + (tone - (tone >> 1));\
}

#endif // INCLUDED_HTFED
