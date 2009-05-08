#!/usr/bin/env python
import optparse
import sys
import numpy
import pyfits
    

def fitsInfo(filePath, showHeader=True, showStats=True):
    """Print information about a FITS file"""
    fitsFile = pyfits.open(filePath)
    if showHeader:
        print "%s header:" % (filePath,)
        hdr = fitsFile[0].header
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
        printArrayStats(filePath, fitsFile[0].data)

def printArrayStats(descr, arr):
    arr = numpy.array(arr)
    print "%s min=%s, max=%s, mean=%s, stdDev=%s" % \
        (descr, arr.min(), arr.max(), arr.mean(), arr.std())


if __name__ == "__main__":
    usageStr = """usage: %%prog [options]

Print information about FITS images (HDU 0 only).
By default prints both the image header and statistics."""
    parser = optparse.OptionParser(usageStr, conflict_handler="resolve")
    parser.add_option("-h", "--header", action="store_true", help="show header")
    parser.add_option("-s", "--stats", action="store_true", help="show statistics")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        sys.exit(0)

    showHeader = options.header
    showStats = options.stats
    if not (showHeader or showStats):
        showHeader = True
        showStats = True
    for filePath in args:
        fitsInfo(filePath, showHeader=showHeader, showStats=showStats)