from __future__ import division, absolute_import
"""Routines to format date and time as ISO date

History:
2010-06-28 ROwen    Bug fix: isoDateFromPySec was broken.
2014-04-25 ROwen    Bug fix: isoDateTimeFromPySec returned an extra 0 before the decimal point if nDig>0.
                    Add from __future__ import division, absolute_import.
"""
import math
import time
import warnings

__all__ = ["isoDateFromPySec", "isoTimeFromPySec", "isoDateTimeFromPySec"]

def isoDateTimeFromPySec(pySec=None, nDig=3, useGMT=True, sepChar="T"):
    """Return the time as an ISO date and time string (without a timezone suffix).
    
    Inputs:
    - pySec: time as returned by time.time(); if None then uses the current time
    - nDig: number of digits of seconds after the decimal point;
        nDig is silently truncated to the range [0, 6]
    - useGMT: treat the time as GMT (ignore the local timezone)?
    - sepChar: character betweend date and time
    
    Returns a string in this format: YYYY-MM-DD<sepChar>HH:MM:SS.ssss
        with nDig digits after the decimal point.
        If nDig = 0 then the decimal point is omitted.
    """
    if nDig < 0:
        nDig = 0
    elif nDig > 6:
        nDig = 6
    
    if pySec == None:
        pySec = time.time()

    roundedSec = round(pySec, nDig)
    if useGMT:
        timeTuple = time.gmtime(roundedSec)
    else:
        timeTuple = time.localtime(roundedSec)

    retStrList = [time.strftime("%%Y-%%m-%%d%s%%H:%%M:%%S" % (sepChar,), timeTuple)]
        
    if nDig > 0:
        fracSec = roundedSec - math.floor(roundedSec)
        fracStr = "%0.*f" % (nDig, fracSec)
        if fracStr[0] == "0":
            retStrList.append(fracStr[1:])
        else:
            # warn with lots of details
            warnings.warn("isoDateTimeFromPySec bug; invalid fractional seconds omitted: " +
                "pySec=%r, roundedSec=%r, fracSec=%r, fracStr=%r" %
                (pySec, roundedSec, fracSec, fracStr))
        
    return "".join(retStrList)

def isoDateFromPySec(pySec=None, useGMT=True):
    """Return the time as an ISO date string (without a timezone suffix).
    
    Inputs:
    - pySec: time as returned by time.time(); if None then uses the current time
    - useGMT: treat the time as GMT, meaning no timezone information is applied
    
    Returns a string in this format: YYYY-MM-DD
    """
    if useGMT:
        timeTuple = time.gmtime(pySec)
    else:
        timeTuple = time.localtime(pySec)

    return time.strftime("%Y-%m-%d", timeTuple)

def isoTimeFromPySec(pySec=None, nDig=3, useGMT=True):
    """Return the time as an ISO time string (without a timezone suffix)
    
    Inputs:
    - pySec: time as returned by time.time(); if None then uses the current time
    - nDig: number of digits of seconds after the decimal point;
        nDig is silently truncated to the range [0, 6]
    - useGMT: treat the time as GMT, meaning no timezone information is applied
    
    Returns a string in this format: HH:MM:SS.ssss
        with nDig digits after the decimal point.
        If nDig = 0 then the decimal point is omitted.
    """
    return isoDateTimeFromPySec(pySec, nDig, useGMT)[11:]
