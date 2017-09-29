#!/usr/bin/env python

"""
Run Astro test code in Astro package.

Warning: does not report a summary at the end;
you'll have to scan the output to see errors!
Eventually I hope to switch to unittest to solve this.
"""
import os
import stat
import subprocess

thisFileName = os.path.basename(__file__)
thisDir = os.path.dirname(__file__)

isFirst = True
for dirpath, dirnames, filenames in os.walk(thisDir):
    # strip invisible directories and files
    newdirnames = [dn for dn in dirnames if not dn.startswith(".")]
    dirnames[:] = newdirnames

    # don't test modules in the root directory
    if isFirst:
        isFirst = False
        continue

    # test all modules
    print("Testing modules in", os.path.basename(dirpath))
    for fileName in filenames:
        if not fileName.endswith(".py"):
            continue
        if fileName.startswith("."):
            continue
        if fileName == thisFileName:
            continue

        filePath = os.path.join(dirpath, fileName)

        if not os.stat(filePath).st_mode & stat.S_IXUSR:
            continue

        print("Testing", filePath)
        subprocess.call(["python", filePath])
