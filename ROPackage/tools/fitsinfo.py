#!/usr/bin/env python
import argparse
import numpy
import pyfits
    

def fitsInfo(filePath, hduList=None, showHeader=True, showStats=True):
    """Print information about a FITS file

    @param[in] filePath: path to FITS file
    @param[in] hduList: list of HDU indices, starting at 0; all if None
    @param[in] showHeader: if True then show the header contents
    @param[in] showStats: if True then show basic image statistics
    """
    fitsFile = pyfits.open(filePath)
    print "*** FITS file %r:" % (filePath,)
    if hduList is None:
        hduList = range(len(fitsFile))

    for hduInd in hduList:
        print "*** HDU %s header:" % (hduInd,)
        fitsExt = fitsFile[hduInd]
        hdr = fitsExt.header
        if showHeader:
            for key, value in hdr.items():
                if key.upper() == "COMMENT":
                    print "%s %s" % (key, value)
                elif isinstance(value, bool):
                    if value:
                        valueStr = "T"
                    else:
                        valueStr = "F"
                    print "%-8s= %s" % (key, valueStr)
                else:
                    print "%-8s= %r" % (key, value)
        if showStats:
            if hdr["NAXIS"] != 2 and fitsExt.header.get("XTENSION") == "BINTABLE":
                print "*** HDU %s statistics:" % (hduInd,)
                printArrayStats(filePath, fitsExt.data)
            else:
                print "*** HDU %s no statistics: not an image" % (hduInd,)

def printArrayStats(descr, arr):
    arr = numpy.array(arr)
    print "%s min=%s, max=%s, mean=%s, stdDev=%s" % \
        (descr, arr.min(), arr.max(), arr.mean(), arr.std())


if __name__ == "__main__":
    usageStr = """Print information about FITS images
By default prints both the image header and statistics for FITS extention 0."""
    parser = argparse.ArgumentParser(usageStr)
    parser.add_argument("files", nargs="+", help="FITS file path(s)")
    parser.add_argument("--header", action="store_true", help="show header")
    parser.add_argument("--stats", action="store_true", help="show statistics")
    parser.add_argument("--hdus", type=int,  nargs="+", default=(0,), help="which HDU(s) to process; 0 by default")
    parsedCmd = parser.parse_args()

    showHeader = parsedCmd.header
    showStats = parsedCmd.stats
    if not (showHeader or showStats):
        showHeader = True
        showStats = True
    for filePath in parsedCmd.files:
        fitsInfo(filePath, showHeader=showHeader, showStats=showStats, hduList=parsedCmd.hdus)