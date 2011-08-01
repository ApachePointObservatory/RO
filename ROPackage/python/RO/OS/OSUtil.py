#!/usr/bin/env python
from __future__ import generators
"""Operating system utilities

History:
2003-03-21 ROwen    splitPath
2003-03-24 ROwen    added walkDirs
2003-04-18 ROwen    added expandFileList; added patWarn arg. to walkDirs.
2003-11-18 ROwen    Modified to use SeqUtil instead of MathUtil.
2004-02-04 ROwen    Renamed to OSUtil and moved into the OS package;
                    added expandPath, realPath and removeDupPaths.
2004-02-05 ROwen    Added exclPatterns to walkDirs.
2004-02-06 ROwen    Combined walkDirs and expandPathList into findFiles
                    and changed recurseDirs to recursionDepth.
2004-05-18 ROwen    Modified splitPath to use var end (it was computed but ignored).
2005-08-02 ROwen    Added getResourceDir
2005-10-07 ROwen    splitPath bug fix: on Windows the first element
                    (disk letter) included a backslash.
2006-08-18 ROwen    Added delDir.
2007-01-17 ROwen    Modified getResourceDir to work with pyinstaller.
2011-08-01 ROwen    findFiles: added arguments dirPatterns and exclDirPatterns; modified to use os.walk.
"""
import os.path
import sys
import fnmatch
import RO.SeqUtil

def delDir(dirPath):
    """Delete dirPath and all contents
    (including symbolic links, but does not follow those links).
    
    Deprecated: use shutil.rmtree instead.
    
    Warning: use with caution; this function can be very destructive.
    
    Based on sample code in the documentation for os.walk.
    """
    if os.path.islink(dirPath):
        raise RuntimeError("%s is a link" % dirPath)
    if not os.path.isdir(dirPath):
        raise RuntimeError("%s is not a directory" % dirPath)

    for root, dirs, files in os.walk(dirPath, topdown=False):
        for name in files:
            fullPath = os.path.join(root, name)
            os.remove(fullPath)
        for name in dirs:
            fullPath = os.path.join(root, name)
            if os.path.islink(fullPath):
                os.remove(fullPath)
            else:
                os.rmdir(fullPath)
    os.rmdir(dirPath)

def expandPath(path):
    """Returns an expanded version of path:
    - follows symbolic links (but not Mac or Windows aliases)
    - expands to a normalized absolute path
    - puts the path into a standard case
    """
    return os.path.normcase(os.path.abspath(realPath(path)))

"""Define a version of os.path.realpath that is available on all platforms.
realPath(path) returns the path after expanding all symbolic links.
Note: does NOT follow Mac or Windows aliases.
"""
try:
    realPath = os.path.realpath
except AttributeError:
    def realPath(path):
        return path

def findFiles(paths, patterns=None, exclPatterns=None, dirPatterns=None, exclDirPatterns=None,
    recursionDepth=None, returnDirs=False, patWarn=False):
    """Search for files that match a given pattern, returning a list of unique paths.
    
    paths may include files and/or directories.
    - All matching directories in paths, and matching subdirectories of same (to the specified recursion depth)
        are searched for files. Matching directories are also included in the output list if returnDirs is true.
    - All matching files in paths or in searched directories are included in the output list.
    
    One use is to handle a list of files that has been dragged and dropped on an applet.

    Inputs:
    - paths: one or a sequence of paths; files are checked to see if they match
        the specified pattern and directories are searched
        if they don't exceed the recursion level
    - patterns: one or a sequence of inclusion patterns; each file name must match at least one of these;
        if None or [] then ["*"] is used.
        Patterns are matched using fnmatch, which does unix-style matching
        (* for any char sequence, ? for one char).
    - exclPatterns: one or a sequence of exclusion patterns; each file name must not match any of these
    - dirPatterns: one or a sequence of inclusion patterns; each directory name must match at least one of these;
        if None or [] then ["*"] is used.
    - exclDirPatterns: one or a sequence of exclusion patterns; each directory name must not match any of these
    - returnDirs: include directories in the returned list?
    - patWarn: print to sys.stderr names of files and directories that don't match the pattern
    
    Notes:
    - Pattern matching is applied to files and directories in the paths argument,
      as well as files and directories in subdirectories.
    - Duplicate paths are removed
    
    Pattern special characters are those for fnmatch:
    *       match any sequence of 0 or more characters
    ?       match any single character
    [seq]   matches any character in seq
    [!seq]  matches any character not in seq
    """
    # process the inputs
    paths = RO.SeqUtil.asSequence(paths)
    patterns = RO.SeqUtil.asSequence(patterns or "*")
    exclPatterns = RO.SeqUtil.asSequence(exclPatterns or ())
    dirPatterns = RO.SeqUtil.asSequence(dirPatterns or "*")
    exclDirPatterns = RO.SeqUtil.asSequence(exclDirPatterns or ())
    if recursionDepth == None:
        recursionDepth = _Inf()
    else:
        recursionDepth = int(recursionDepth)

    # perform the search
    foundPathList = []
    for path in paths:
        if os.path.isfile(path):
            if _nameMatch(path, patterns, exclPatterns):
                foundPathList.append(path)
            elif patWarn:
                sys.stderr.write("Skipping file %r: no pattern match\n" % (path,))
        elif os.path.isdir(path):
            strippedPath = path.rstrip(os.path.sep)
            baseLevel = strippedPath.count(os.path.sep)
            if _nameMatch(path, dirPatterns, exclDirPatterns):
                if returnDirs:
                    foundPathList.append(path)
                for root, dirs, files in os.walk(path):
                    newDirs = []
                    subLevel = root.count(os.path.sep)
                    if recursionDepth != None and subLevel - baseLevel >= recursionDepth:
                        del dirs[:]
                    else:
                        for d in dirs:
                            dPath = os.path.join(root, d)
                            if _nameMatch(d, dirPatterns, exclDirPatterns):
                                newDirs.append(d)
                                if returnDirs:
                                    foundPathList.append(dPath)
                            elif patWarn:
                                sys.stderr.write("Skipping dir %r: no pattern match\n" % (dPath,))
                        if len(dirs) > len(newDirs):
                            dirs[:] = newDirs

                    for f in files:
                        fPath = os.path.join(root, f)
                        if _nameMatch(f, patterns, exclPatterns):
                            foundPathList.append(fPath)
                        elif patWarn:
                            sys.stderr.write("Skipping file %r: no pattern match\n" % (fPath,))
            elif patWarn:
                sys.stderr.write("Skipping dir %r: no pattern match\n" % (path,))
        elif not os.path.exists(path):
            sys.stderr.write("Warning: file does not exist: %s\n" % path)
        else:
            sys.stderr.write("Skipping non-file, non-directory: %s\n" % path)
    
    return removeDupPaths(foundPathList)

def getResourceDir(pkg, *args):
    """Return a directory of resources for a package,
    assuming the following layout:
    
    For source code in <pkgRoot>:
    - The resources are in <pkgRoot>/pkg/arg0/arg1...
    
    For a py2app or py2exe distribution <distRoot>:
    - The package is in <distRoot>/<something>.zip/pkg
    - The resources are in <distRoot>/pkg/arg0/arg1/...
    
    For a pyinstaller distribution <distRoot>:
    - sys.executable points to <distRoot>/<executable>
      (but see warning below)
    - The resources are in <distRoot>/pkg/arg0/arg1/...
    
    Warning for pyinstaller users:
    pyinstaller uses sys.executable to find modules
    (because <module>.__file__ is wrong in pyinstaller 1.3).
    However, pyinstaller 1.3 sets sys.executable to a relative path,
    which means it will be wrong if you change the
    current working directory.
    To be safe, always start your program with:
    
    # hack for pyinstaller 1.3
    sys.executable = os.path.abspath(sys.executable)
    """
    sysFrozen = getattr(sys, "frozen", None)
    if sysFrozen == 1:
        # handle pyinstaller; pkg.__file__ is dead wrong
        pkgRoot = os.path.dirname(sys.executable)
        if not os.path.isdir(pkgRoot):
            raise RuntimeError(
"""You are using pyinstaller and
    sys.executable=%r
cannot be found. To fix this please put:
    sys.executable = os.path.abspath(sys.executable)
at the beginning of your code.""" % (sys.executable,)
)
    else:
        pkgRoot = os.path.dirname(os.path.dirname(pkg.__file__))
        if pkgRoot.lower().endswith(".zip"):
            # handle py2app and py2exe
            pkgRoot = os.path.dirname(pkgRoot)
    return os.path.join(pkgRoot, pkg.__name__, *args)

def removeDupPaths(pathList):
    """Returns a copy of pathList with duplicates removed.

    To compare two paths, both are first resolved as follows:
    - follows symbolic links (but not Mac or Windows aliases)
    - expands to a normalized absolute path
    - puts into a standard case
    However, the original path names are used in the returned
    list (and the original order is preserved, barring duplicates).
    """


    expDict = {}
    outList = []
    for path in pathList:
        expPath = expandPath(path)
        if expPath not in expDict:
            expDict[expPath] = None
            outList.append(path)
    return outList

def splitPath(path):
    """Splits a path into its component pieces.
    Similar to os.path.split but breaks the path completely apart
    instead of into just two pieces.
    
    My code with a correction from a Python Cookbook recipe by Trent Mick
    
    Note: pathList is built backwards and then reversed because
    inserting is much more expensive than appending to lists.
    """
    pathList = []
    while True:
        head, tail = os.path.split(path)
        if "" in (head, tail):
            end = head or tail
            if end.endswith(os.sep):
                end = end[:-1]
            if end:
                pathList.append(end)
            break
            
        pathList.append(tail)
        path = head
    pathList.reverse()
    return pathList

def openUniv(path):
    """Opens a text file for reading in universal newline mode, if possible;
    silently opens without universal mode for Python versions < 2.3.
    """
    if sys.version_info[0:2] >= (2,3):
        # use universal newline support (new in Python 2.3)
        openMode = 'rU'
    else:
        openMode = 'r'
    return open(path, openMode)

class _Inf:
    def __gt__(self, other):
        return True
    def __ge__(self, other):
        return True
    def __eq__(self, other):
        return isinstance(other, _Inf)
    def __ne__(self, other):
        return not isinstance(other, _Inf)
    def __le__(self, other):
        return isinstance(other, _Inf)
    def __lt__(self, other):
        return False
    def __add__(self, other):
        return self
    def __sub__(self, other):
        return self
    def __mul__(self, other):
        return self
    def __div__(self, other):
        return self
    def __str__(self):
        return "inf"
    def __int__(self):
        return self
    def __long__(self):
        return self
    def __float__(self):
        return self

def _nameMatch(path, patterns, exclPatterns):
    """Check if file name matches a set of patterns.
    
    Returns True if baseName matches any pattern in patterns
    and does not match any pattern in exclPatterns.
    Matching is done by fnmatch.fnmatch.
    
    Also returns True if there are no patterns or exclPatterns.
    
    Does no verification of any input.
    """
#   print "_nameMatch(%r, %r, %r)" % (path, patterns, exclPatterns)
    baseName = os.path.basename(path)
    for pat in patterns:
        if fnmatch.fnmatch(baseName, pat):
            for exclPat in exclPatterns:
                if fnmatch.fnmatch(baseName, exclPat):
                    return False
            return True
    return False    
