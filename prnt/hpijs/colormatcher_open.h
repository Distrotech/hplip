/*****************************************************************************\
  colormatcher_open.h : Interface for the ColorMatcher_Open class

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


#ifndef APDK_COLORMATCHER_OPEN_H
#define APDK_COLORMATCHER_OPEN_H

APDK_BEGIN_NAMESPACE

class ColorMatcher_Open : public ColorMatcher
{
public:
    ColorMatcher_Open(SystemServices* pSys,
        ColorMap cm,unsigned int DyeCount,
        unsigned int iInputWidth);
    virtual ~ColorMatcher_Open();

protected:

    void Interpolate(const uint32_t *map,
        unsigned char r,unsigned char g,unsigned char b,
        unsigned char *blackout, unsigned char *cyanout,
        unsigned char *magentaout, unsigned char *yellowout);

    void Interpolate(const unsigned char *map,
        unsigned char r,unsigned char g,unsigned char b,
        unsigned char *blackout, unsigned char *cyanout,
        unsigned char *magentaout, unsigned char *yellowout);


}; //ColorMatcher_Open

APDK_END_NAMESPACE

#endif //APDK_COLORMATCHER_OPEN_H
