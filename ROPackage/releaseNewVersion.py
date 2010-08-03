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
import tarfile

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
print "Building test build"
status = subprocess.call(["python", "setup.py", "sdist"])
if status != 0:
    print "Test build failed!"

# make sure the bitmap files got into the distribution
# (sometimes they fail to, and it's a silent error unless I check)
distDir = os.path.abspath("dist")
distBaseName = "RO-%s" % (Version.__version__,)
distPath = os.path.join(distDir, distBaseName + ".tar.gz")
tarObj = tarfile.open(distPath)
bitmapToFind = "%s/python/RO/Bitmaps/crosshair.xbm" % (distBaseName,)
try:
    tarObj.getmember(bitmapToFind)
except Exception:
    print "Error: distribution is missing its bitmap files!"
    sys.exit(1)


print "Deleting test build %r" % (distDir,)
shutil.rmtree(distDir)

print "Building final build and uploading"
status = subprocess.call(["python", "setup.py", "sdist", "upload", "--show-response"])
if status != 0:
    print "Build and upload failed!"

eggDir = os.path.abspath("RO.egg-info")

print "Deleting final build %r" % (distDir,)
shutil.rmtree(distDir)

print "Deleting egg info %r" % (eggDir,)
shutil.rmtree(eggDir)
