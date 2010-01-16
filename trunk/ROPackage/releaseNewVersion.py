#!/usr/bin/env python
"""A script to release a new version of RO Python Package and upload it to PyPI

To use:
    ./releaseNewVersion.py
"""
from __future__ import with_statement
import os
import re
import shutil
import sys
import subprocess

PkgRoot = "python"
PkgName = "RO"
PkgDir = os.path.join(PkgRoot, PkgName)
sys.path.insert(0, PkgDir)
import Version
queryStr = "Version from RO.Version = %s; is this OK? (y/[n]) " % (Version.__version__,)
versOK = raw_input(queryStr)
if not versOK.lower() == "y":
    sys.exit(0)

versRegEx = re.compile(r"<h3>(\d.*?)\s+\d\d\d\d-\d\d-\d\d</h3>")
with file(os.path.join("docs", "VersionHistory.html")) as vhist:
    for line in vhist:
        versMatch = versRegEx.match(line)
        if versMatch:
            histVersStr = versMatch.groups()[0]
            if histVersStr == Version.__version__:
                print "Version in VersionHistory.html matches"
                break
            else:
                print "Error: version in VersionHistory.html = %s != %s" % (histVersStr, Version.__version__)
                sys.exit(0)

print "Status of subversion repository:"

subprocess.call(["svn", "status"])

versOK = raw_input("Is the subversion repository up to date? (y/[n]) ")
if not versOK.lower() == "y":
    sys.exit(0)

print "Subversion repository OK"

# warning: do not build from export because the svn info is required to get the data files included
print "Building, uploading and registering"
status = subprocess.call(["python", "setup.py", "sdist", "upload", "--show-response"])
if status != 0:
    print "Build and upload failed!"

distDir = os.path.abspath("dist")
eggDir = os.path.abspath("RO.egg-info")
delOK = raw_input("OK to delete %r and %r? (y/[n]) " % (distDir, eggDir))
if not delOK.lower() == "y":
    sys.exit(0)

print "Deleting %r" % (distDir,)
shutil.rmtree(distDir)

print "Deleting %r" % (eggDir,)
shutil.rmtree(eggDir)

