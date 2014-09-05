from __future__ import division, absolute_import
from RO.Astro import llv

__all__ = ["mjdFromEpJ"]

def mjdFromEpJ (epj):
    """
    Converts Julian epoch to Modified Julian Date.
    
    Inputs:
    - epj   Julian epoch
    
    Returns:
    - mjd   Modified Julian Date (JD - 2400000.5).
    
    History:
    2002-08-06 ROwen    Just a more memorable name for llv.epj2d.
    2014-04-25 ROwen    Add from __future__ import division, absolute_import.
    """
    return llv.epj2d(epj)
