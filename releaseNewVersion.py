#!/usr/bin/env python
from __future__ import absolute_import, division, print_function
"""A script to release a new version of RO Python Package and upload it to PyPI

To use:
    ./releaseNewVersion.py
"""
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
                print("Version in VersionHistory.html matches")
                break
            else:
                print("Error: version in VersionHistory.html = %s != %s" % (histVersStr, Version.__version__))
                sys.exit(0)

print("Status of git repository:")

subprocess.call(["git", "status"])

versOK = raw_input("Is the git repository up to date? (y/[n]) ")
if not versOK.lower() == "y":
    sys.exit(0)

print("git repository OK")

# warning: do not build from export because the git info is required to get the data files included
print("Building the distribution package")
status = subprocess.call(["python", "setup.py", "sdist"])
if status != 0:
    print("Build failed!")

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
    print("Error: distribution is missing its bitmap files!")
    sys.exit(1)

print("Uploading to PyPI")
status = subprocess.call(["twine", "upload", "dist/%s.tar.gz" % (distBaseName,)])
if status != 0:
    print("Upload failed!")
    sys.exit(1)

eggDir = os.path.abspath("RO.egg-info")

print("Deleting final build %r" % (distDir,))
shutil.rmtree(distDir)

print("Deleting egg info %r" % (eggDir,))
shutil.rmtree(eggDir)

print("***** Update documentation on the UW server! *****")
