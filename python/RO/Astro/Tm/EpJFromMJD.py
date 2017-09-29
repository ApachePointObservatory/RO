#!/usr/bin/env python


__all__ = ["epJFromMJD"]

from RO.Astro import llv

def epJFromMJD (mjd):
    """
    Converts Modified Julian Date to Julian epoch.

    Inputs:
    - mjd   Modified Julian Date (JD - 2400000.5)

    Returns:
    - epj   Julian epoch.

    History:
    2002-08-06 ROwen    Just a more memorable name for llv.epj.
    2014-04-25 ROwen    Add from __future__ import division, absolute_import.
    """
    return llv.epj(mjd)
