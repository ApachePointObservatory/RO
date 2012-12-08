#!/usr/bin/env python
import time
import RO.PhysConst

__all__ = ["setClockError", "getClockError", "getCurrPySec", "utcFromPySec", "pySecFromUTC"]

# Python time tuple for J2000: 2000-01-01 12:00:00 (a Saturday)
_TimeTupleJ2000 = (2000, 1, 1, 12, 0, 0, 5, 1, 0)
_TimeError = 0.0 # time reported by your computer's clock - actual time (seconds)

def setClockError(timeError):
    """Set clock error.
    
    Inputs:
    - timeError: computer clock error (seconds): time reported by your computer's clock - actual time
    
    This module starts out with a time error of 0, which is correct for most computers
    (any with a functioning NTP time server pointing to a normal time server).
    Two occasions when you might wish to set a nonzero value:
    - If the computer is not keeping time for some reason (e.g. it is not using an NTP server)
    - The computer is keeping some time other than UTC. For instance some observatories
      keep their computer clocks on TAI or another uniform time system to avoid leap seconds.
      If the computer is keeping TAI then timeError should be TAI-UTC, in seconds.
    """
    global _TimeError
    _TimeError = float(timeError)
    
def getClockError():
    """Get clock error
    
    Return computer clock error (seconds): time reported by your computer's clock - actual time
    """
    global _TimeError
    return _TimeError

def getCurrPySec(uncorrTime=None):
    """Get current python time with time error correction applied
    
    Input:
    - uncorrTime: python time without correction applied; if None then current time is used
    """
    if uncorrTime is None:
        uncorrTime = time.time()
    return uncorrTime - _TimeError

def utcFromPySec(pySec = None):
    """Returns the UTC (MJD) corresponding to the supplied python time, or now if none.
    """
    global _TimeTupleJ2000

    if pySec == None:
        pySec = getCurrPySec()
    
    # python time (in seconds) corresponding to 2000-01-01 00:00:00
    # this is probably constant, but there's some chance
    # that on some computer systems it varies with daylights savings time
    pySecJ2000 = time.mktime(_TimeTupleJ2000) - time.timezone
    
    return RO.PhysConst.MJDJ2000 + ((pySec - pySecJ2000) / RO.PhysConst.SecPerDay)

def pySecFromUTC(utcDays):
    """Returns the python time corresponding to the supplied UTC (MJD).
    """
    global _TimeTupleJ2000

    pySecJ2000 = time.mktime(_TimeTupleJ2000) - time.timezone

    return ((utcDays - RO.PhysConst.MJDJ2000) * RO.PhysConst.SecPerDay) + pySecJ2000
