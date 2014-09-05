from __future__ import division, absolute_import
"""Functions to convert to/from TAI

History:
2014-04-25 ROwen    Add from __future__ import division, absolute_import and use relative import.
"""
import RO.PhysConst
from .UTCFromPySec import utcFromPySec, pySecFromUTC

__all__ = ["getUTCMinusTAI", "setUTCMinusTAI", "taiFromPySec", "utcFromTAI", "taiFromPySec", "pySecFromTAI"]

# global variable UTC-TAI (since leap seconds are unpredictable)
# set to some initial plausible value and update with setUTCMinusTAI
_UTCMinusTAIDays = -35 / float(RO.PhysConst.SecPerDay) # a reasonable value correct as of 2012-12

def getUTCMinusTAI():
    """Return UTC - TAI (in seconds).
    
    Warning: the value will only be correct if it was properly set by setUTCMinusTAI
    """
    return _UTCMinusTAIDays * RO.PhysConst.SecPerDay

def setUTCMinusTAI(newUTCMinusTAISec):
    """Set UTC - TAI (in seconds)"""
    global _UTCMinusTAIDays
    _UTCMinusTAIDays = newUTCMinusTAISec / float(RO.PhysConst.SecPerDay)

def taiFromUTC(utc):
    """Convert UTC (MJD) to TAI (MJD)"""
    global _UTCMinusTAIDays
    return utc - _UTCMinusTAIDays

def utcFromTAI(tai):
    """Convert TAI (MJD) to UTC (MJD)"""
    global _UTCMinusTAIDays
    return tai + _UTCMinusTAIDays

def taiFromPySec(pySec=None):
    """Convert python seconds (now if None) to TAI (MJD)"""
    return taiFromUTC(utcFromPySec(pySec))

def pySecFromTAI(tai):
    """Convert TAI (MJD) to python seconds"""
    return pySecFromUTC(utcFromTAI(tai))
