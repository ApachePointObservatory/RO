#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
"""Run a script as a droplet (an application onto which you drop file) with a log window

On Mac OS X additional files may be dropped on the application icon once the first batch is processed.
I don't know how to support this on other platforms.
"""
import sys

if __name__ == "__main__":
    print("sample droplet received %s files:" % (len(sys.argv)-1))
    for filePath in sys.argv[1:]:
        print("   ", filePath)
