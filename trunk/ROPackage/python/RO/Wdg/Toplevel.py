#!/usr/bin/env python
"""RO.Wdg.Toplevel wdigets are windows with some enhanced functionality, including:
- Remembers last geometry if closed or iconified
- Can record geometry, visibility and widget state in a file

History:
2002-03-18 ROwen    First release.
2002-04-29 ROwen    Added "ToplevelSet".
2002-04-30 ROwen    Added wdgFunc argument to Toplevel.
2003-03-21 ROwen    Changed to allow resizable = True/False;
                    fixed a bug wherein geometry strings with +- or -+ were being rejected;
                    added Debug constant for more robust launching.
2003-03-25 ROwen    Added ability to create geom file if none exists
2003-06-18 ROwen    Modified to print at traceback and go on when the toplevel's widget
                    function fails; the test now excludes SystemExit and KeyboardInterrupt
2003-06-19 ROwen    Now saves window open/closed.
2003-11-18 ROwen    Modified to use SeqUtil instead of MathUtil.
2003-12-18 ROwen    Size is now saved and restored for windows with only one axis resizable.
                    Changed getGeometry to always return the entire geometry string.
2004-02-23 ROwen    Preference files are now read with universal newline support
                    on Python 2.3 or later.
2004-03-05 ROwen    Modified to use RO.OS.univOpen.
2004-05-18 ROwen    Bug fix in ToplevelSet: referred to defGeomFixDict instead of defGeomVisDict.
2004-07-16 ROwen    Modified Toplevel to propogate the exception if wdgFunc fails.
                    As a result, ToplevelSet.createToplevel no longer creates an erroneous
                    entry to a nonexistent toplevel if wdgFunc fails.
                    Bug fix: ToplevelSet could not handle toplevels that were destroyed.
                    Various methods modified to use getToplevel(name) to get the tl,
                    and if None is returned then the tl never existed or has been destroyed.
2004-08-11 ROwen    Renamed Close... constants to tl_Close...
                    Define __all__ to restrict import.
2005-06-08 ROwen    Changed ToplevelSet to a new-style class.
2005-10-18 ROwen    Fixed doc error: width, height ignored only if not resizable in that dir.
2006-04-26 ROwen    Added a patch (an extra call to update_idletasks) for a bug in Tcl/Tk 8.4.13
                    that caused certain toplevels to be displayed in the wrong place.
                    Removed a patch in makeVisible for an older tk bug; the patch
                    was now causing iconified toplevels to be left iconified.
                    Always pack the widget with expand="yes", fill="both";
                    this helps the user creates a window first and then makes it resizable.
                    Commented out code in makeVisible that supposedly avoids toplevels shifting;
                    I can't see how it can help.
2007-08-16 ROwen    Added a workaround for Tk Toolkit bug 1771916: Bad geometry reported...;
                    __recordGeometry prints a warning and does not save geometry if y < 0.
2007-09-05 ROwen    Added Toplevel.__str__ method and updated debug print statements to use it.
                    Added missing final \n to Toplevel.__recordGeometry's y < 0 warning.
2009-04-20 ROwen    Bug fix: Toplevels with tl_CloseDisabled could be iconified using the standard keystroke.
2010-05-05 ROwen    Modified to display Toplevels within the visible screen area, even if the requested
                    geometry is not (as can easily happen if you sometimes connect a laptop to an external
                    monitor). The code assumes your visible screen is a rectangle, so it can be fooled
                    by strange screen arrangements.
2010-06-28 ROwen    Removed one unused import (thanks to pychecker).
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code
2011-08-11 ROwen    Added support for saving and restoring widget state.
                    Made error handling safer by using RO.StringUtil.strFromException.
2011-08-19 ROwen    Support Python < 2.6 by importing simplejson if json not found.
2012-07-10 ROwen    Removed used of update_idletasks; used a different technique to fix the problem
                    that windows that are only resizable in one dimension are sometimes drawn incorrectly.
2014-02-12 ROwen    Added getNamesInGeomFile method to ToplevelSet.
"""
__all__ = ['tl_CloseDestroys', 'tl_CloseWithdraws', 'tl_CloseDisabled', 'Toplevel', 'ToplevelSet']

try:
    import json
except Exception:
    import simplejson as json
import os.path
import sys
import traceback
import Tkinter
import RO.CnvUtil
import RO.OS
import RO.SeqUtil
import RO.StringUtil
import RO.TkUtil

# constants for the closeMode argument
tl_CloseDestroys = 0
tl_CloseWithdraws = 1
tl_CloseDisabled = 2

class Toplevel(Tkinter.Toplevel):
    def __init__(self,
        master=None,
        geometry="",
        title=None,
        visible=True,
        resizable=True,
        closeMode=tl_CloseWithdraws,
        wdgFunc=None,
        doSaveState=False,
    ):
        """Creates a new Toplevel. Inputs are:
        - master: master window; if omitted, root is used
        - geometry: Tk geometry string: WxH+-X+-Y;
          width and/or height are ignored if the window is not resizable in that direction
        - title: title of window
        - visible: display the window?
        - resizable: any of:
            - True (window can be resized)
            - False (window cannot be resized)
            - pair of bool: x, y dimension resizable by user?
        - closeMode: this is one of:
          - tl_CloseDestroys: close destroys the window and contents, as usual
          - tl_CloseWithdraws (default): close withdraws the window, but does not destroy it
          - tl_CloseDisabled: close does nothing
        - wdgFunc: a function which, when called with the toplevel as its only argument,
          creates a widget which is to be packed into the Toplevel.
          The widget is packed to grow as required based on resizable.
        - doSaveState: save window state in the geometry file? If True then you must provide wdgFunc
            and the widget it returns must support this method:
            - getStateTracker(): return an RO.Wdg.StateTracker object
            State is saved in the geometry file as a JSon encoding of the dict.
          
        Typically one uses RO.Alg.GenericCallback or something similar to generate wdgFunc,
        for example: GenericFunction(Tkinter.Label, text="this is a label").
        But BEWARE!!! if you use GenericCallback then you must give it NAMED ARGUMENTS ONLY.
        This is because GenericCallback puts unnamed saved (specified in advance) arguments first,
        but the master widget (which is passed in later) must be first.
        
        An alternative solution is to create a variant of GenericCallback that
        is specialized for Tk widgets or at least puts unnamed dynamic arguments first.
        """
        Tkinter.Toplevel.__init__(self, master)
        self.wm_withdraw()
        
        resizable = RO.SeqUtil.oneOrNAsList(resizable, 2, valDescr = "resizable")
        resizable = tuple([bool(rsz) for rsz in resizable])
        self.__canResize = resizable[0] or resizable[1]
        self.__geometry = ""
        self.__wdg = None  # contained widget, but only if wdgFunc specified
        self._reportedBadPosition = False
        self._defState = {}
        self._stateTracker = None

        if title:
            self.wm_title(title)
        self.wm_resizable(*resizable)
        
        self.bind("<Unmap>", self.__recordGeometry)
        self.bind("<Destroy>", self.__recordGeometry)
        
        # handle special close modes
        self.__closeMode = closeMode  # save in case someone wants to look it up
        if self.__closeMode == tl_CloseDisabled:
            def noop():
                pass
            self.protocol("WM_DELETE_WINDOW", noop)
            def stopEvent(evt=None):
                return "break"
            self.bind("<<Close>>", stopEvent)
        elif self.__closeMode == tl_CloseWithdraws:
            self.protocol("WM_DELETE_WINDOW", self.withdraw)
        
        # if a widget creation function supplied, use it
        if wdgFunc:
            try:
                self.__wdg = wdgFunc(self)
                self.__wdg.pack(expand="yes", fill="both")
            except Exception, e:
                sys.stderr.write("Could not create window %r: %s\n" % (title, RO.StringUtil.strFromException(e)))
                traceback.print_exc(file=sys.stderr)
                raise
            if doSaveState:
                self._stateTracker = self.__wdg.getStateTracker()
                if self._stateTracker == None:
                    raise RuntimeError("getStateTracker returned None")
                    
            
        elif doSaveState:
            raise RuntimeError("You must provide wdgFunc if you specify doSaveState True")

        # Once window initial size is set, shrink-wrap behavior
        # goes away in both dimensions. If the window can only be
        # resized in one direction, the following bindings
        # restore shrink-wrap behavior in the other dimension.
        if self.__canResize:
            if not resizable[0]:
                # must explicitly keep width correct
                self.bind("<Configure>", self.__adjWidth)
            elif not resizable[1]:
                # must explicitly keep height correct
                self.bind("<Configure>", self.__adjHeight)

        # making the window visible after setting everything else up works around several glitches:
        # - one of my windows was showing up in the wrong location, only on MacOS X aqua, for no obvious reason
        # - some windows with only one axis resizable were showing up with the wrong size
        if visible:
            self.setGeometry(geometry)
            self.makeVisible()
        else:
            self.setGeometry(geometry)
        
        # it is unlikely that the state will depend on the geometry, but just in case,
        # record the default state last
        if self.getDoSaveState():
            self._defState = self._stateTracker.getState()
    
    def setGeometry(self, geomStr):
        """Set the geometry of the window based on a Tk geometry string.

        Similar to the standard geometry method, but:
        - constrains the entire toplevel to be on screen
          (if size information is missing, then makes sure some of the toplevel is on screen)
        - sets only position information if window is self-sizing
        - records the new geometry (including size information, even if window is self-sizing)
        """
        #print "%s.setGeometry(%s)" % (self, geomStr,)
        if not geomStr:
            return
        geom = RO.TkUtil.Geometry.fromTkStr(geomStr).constrained()
        if self.__canResize:
            includeExtent = None # supply if available, else omit
        else:
            includeExtent = False
        constrainedGeomStr = geom.toTkStr(includeExtent=includeExtent)
        #print "%s.setGeometry: constrained geometry = %s" % (self, constrainedGeomStr)
        self.geometry(constrainedGeomStr)
        if not self.getVisible():
            self.__geometry = geom.toTkStr(includeExtent=None)
    
    def __recordGeometry(self, evt=None):
        """Record the current geometry of the window.
        """
        #print "%s.__recordGeometry; geom=%s" % (self, self.geometry())
        if self.winfo_y() < 0:
            if not self._reportedBadPosition:
                self._reportedBadPosition = True
                sys.stderr.write("%s y position < 0; not saving geometry\n" % (self,))
            return

        self.__geometry = self.geometry()
        self._reportedBadPosition = False
    
    def __adjWidth(self, evt=None):
        """Update geometry to shrink-to-fit width and user-requested height
        
        Use as the binding for <Configure> if resizable = (True, False).
        """
        height = self.winfo_height()
        if height < 2:
            return
        reqwidth = self.winfo_reqwidth()
        if self.winfo_width() != reqwidth:
            self.geometry("%sx%s" % (reqwidth, height))
    
    def __adjHeight(self, evt=None):
        """Update geometry to shrink-to-fit height and user-requested width
        
        Use as the binding for <Configure> if resizable = (False, True).
        """
        width = self.winfo_width()
        if width < 2:
            return
        reqheight = self.winfo_reqheight()
        if self.winfo_height() != reqheight:
            self.geometry("%sx%s" % (width, reqheight))
    
    def getVisible(self):
        """Returns True if the window is visible, False otherwise
        """
        return self.winfo_exists() and self.winfo_ismapped()
    
    def getGeometry(self):
        """Returns the geometry string of the window.
        
        Similar to the standard geometry method, but:
        - If the window is visible, the geometry is recorded as well as returned.
        - If the winow is not visible, the last recorded geometry is returned.
        - If the window was never displayed, returns the initial geometry
          specified, if any, else ""
        
        The position is measured in pixels from the upper-left-hand corner.
        """
        if self.getVisible():
            self.__recordGeometry()
        return self.__geometry
    
    def getDoSaveState(self):
        """Returns True if saving state
        """
        return self._stateTracker != None
    
    def getStateIsDefault(self):
        """Returns the state dictionary of the underlying widget and a flag indicating if default
        
        Returns three items:
        - stateDict: the state dictionary of the underlying widget, or {} if not saving state
        - isDefault: a flag indicating whether the state is the default state;
            always True if not saving state
        
        Raise RuntimeError if not saving state
        """
        if not self.getDoSaveState():
            raise RuntimeError("Not saving state")
        stateDict = self._stateTracker.getState()
        isDefault = stateDict == self._defState
#         print "getStateIsDefault: stateDict=%s, self._defState=%s, isDefault=%s" % (stateDict, self._defState, isDefault)
        return stateDict, isDefault

    def setState(self, stateDict):
        """Set the state dictionary of the underlying widget
        
        Raise RuntimeError if not saving state
        """
        if not self.getDoSaveState():
            raise RuntimeError("Not saving state")
        self._stateTracker.setState(stateDict)
        
    def getWdg(self):
        """Returns the contained widget, if it was specified at creation with wdgFunc.
        Please use with caution; this is primarily intended for debugging.
        """
        return self.__wdg
    
    def makeVisible(self):
        """Displays the window, if withdrawn or deiconified, or raises it if already visible.
        """
        if self.wm_state() == "normal":
            # window is visible
            self.lift()  # note: the equivalent tk command is "raise"
        else:           
            # window is withdrawn or iconified
            # At one time I set the geometry first "to avoid displaying and then moving it"
            # but I can't remember why this was useful; meanwhile I've commented it out
#           self.setGeometry(self.__geometry)
            self.wm_deiconify()
            self.lift()
    
    def __printInfo(self):
        """A debugging tool prints info to the main window"""
        print "info for RO.Wdg.Toplevel %s" % self.wm_title()
        print "getGeometry = %r" % (self.getGeometry(),)
        print "geometry = %r" % (self.geometry())
        print "width, height = %r, %r" % (self.winfo_width(), self.winfo_height())
        print "req width, req height = %r, %r" % (self.winfo_reqwidth(), self.winfo_reqheight())

    def __str__(self):
        return "Toplevel(%s)" % (self.wm_title(),)


class ToplevelSet(object):
    """A set of Toplevel windows that can record and restore positions to a file.
    """
    def __init__(self,
        fileName = None,
        defGeomVisDict = None,
        createFile = False,
    ):
        """Create a ToplevelSet
        Inputs:
        - fileName: full path to a file of geometry and visiblity info
            (see readGeomVisFile for file format);
            the file is read initially and the file name is the default for readGeomVisFile
        - defGeomVisDict: default geometry and visible info, as a dictionary
            whose keys are window names and values are tuples of:
            - Tk geometry strings: WxH+-X+-Y; None or "" for no default
            - visible flag; None for no default
        - createFile: if the geometry file does not exist, create a new blank one?
        """
        
        self.defFileName = fileName

        # geometry, visibility and state dictionaries
        # the file dictionaries contain data read from the geom/vis file
        # the default dictionaries contain programmer-supplied defaults
        # (there is no default state dict because default state is obtained from the Toplevel)
        # file data overrides programmer defaults
        # all dictionaries have name as the key
        # Geom dictionaries have a Tk geometry string as the value
        # Vis dictionaries have a boolean as the value
        # fileState has a state dictionary as the value
        self.fileGeomDict = {}
        self.fileVisDict = {}
        self.fileState = {}
        self.defGeomDict = {}
        self.defVisDict = {}
        if defGeomVisDict:
            for name, geomVis in defGeomVisDict.iteritems():
                geom, vis = geomVis
                if geom:
                    self.defGeomDict[name] = geom
                if vis:
                    self.defVisDict[name] = vis

        self.tlDict = {}    # dictionary of name:toplevel items
        if self.defFileName:
            self.readGeomVisFile(fileName, createFile)
    
    def addToplevel(self,
        toplevel,
        name,
    ):
        """Adds a new Toplevel instance to the set.
        """
        if self.getToplevel(name):
            raise RuntimeError, "toplevel %r already exists" % (name,)
        self.tlDict[name] = toplevel
    
    def createToplevel(self, 
        name,
        master=None,
        defGeom="",
        defVisible=None,
        **kargs):
        """Create a new Toplevel, add it to the set and return it.
        
        Inputs are:
        - name: unique identifier for Toplevel.
            If you don't specify a separate title in kargs,
            the Toplevel's title is the last period-delimited field in name.
            This allows you to specify a category and a title, e.g. "Inst.Spicam".
        - defGeom: default Tk geometry string: WxH+-X+-Y;
            added to the default geometry dictionary
            (replacing the current entry, if any)
          width and height are ignored unless window is fully resizable
        - defVisible: default value for visible;
            added to the default visible dictionary
            (replacing the current entry, if any)
        - **kargs: keyword arguments for Toplevel, which see;
            note that visible is ignored unless defVisible is omitted
            and visible exists, in which case defVisible = visible
        
        Return the new Toplevel
        """
        if self.getToplevel(name):
            raise RuntimeError, "toplevel %r already exists" % (name,)
        if defGeom:
            self.defGeomDict[name] = defGeom
        if defVisible == None:
            # if defVisible omitted, see if visible specified
            defVisible = kargs.get("visible", None)
        if defVisible != None:
            # if we have a default visibility, put it in the dictionary
            self.defVisDict[name] = bool(defVisible)
        geom = self.getDesGeom(name)
        kargs["visible"] = self.getDesVisible(name)
        if "title" not in kargs:
            kargs["title"] = name.split(".")[-1]
        #print "ToplevelSet is creating %r with master = %r, geom= %r, kargs = %r" % (name, master, geom, kargs)
        newToplevel = Toplevel(master, geom, **kargs)
        
        # restore state, if appropriate
        if newToplevel.getDoSaveState():
            stateDict = self.fileState.get(name)
            if stateDict != None:
#                 print "restoring state for Toplevel %s: %s" % (name, stateDict)
                newToplevel.setState(stateDict)
#             else:
#                 print "no saved state for Toplevel %s" % (name,)
            
        self.tlDict[name] = newToplevel
        return newToplevel
    
    def getDesGeom(self, name):
        """Return the desired geometry for the named toplevel, or "" if none.
        
        Inputs:
        - name: name of toplevel
        
        Returns geometry in standard Tk format: <width>x<height>[+/-<x0>+/-<x0>]
        where +/- means + or - and the extent information in [] may be missing.
        
        The desired geometry is the entry in the geometry file (if any),
        else the entry in the default geometry dictionary.
        
        Warning: the desired geometry may be entirely off screen.
        Eventually I hope to constrain it.
        """
        desGeom = self.fileGeomDict.get(name, self.defGeomDict.get(name, ""))
        return desGeom
    
    def getDesVisible(self, name):
        """Return the desired visiblity for the named toplevel, or True if none.
        
        The desired visibility is the entry in the geom/vis file (if any),
        else the entry in the default visibility dictionary.
        """
        return self.fileVisDict.get(name, self.defVisDict.get(name, True))

    def getToplevel(self, name):
        """Return the named Toplevel, or None of it does not exist.
        """
        tl = self.tlDict.get(name, None)
        if not tl:
            return None
        if not tl.winfo_exists():
            del self.tlDict[name]
            return None
        return tl
    
    def getNames(self, prefix=""):
        """Return all window names of windows that start with the specified prefix
        (or all names if prefix omitted). The names are in alphabetical order
        (though someday that may change to the order in which windows are added).
        
        The list includes toplevels that have been destroyed.
        """
        nameList = self.tlDict.keys()
        nameList.sort()
        if not prefix:
            return nameList
        return [name for name in nameList if name.startswith(prefix)]

    def getNamesInGeomFile(self, prefix=""):
        """Return all window names in the geometry file that start with the specified prefix
        (or all names if prefix omitted). The names are in alphabetical order
        (though someday that may change to the order in which windows are added).
        """
        nameList = sorted(self.fileGeomDict.iterkeys())
        if not prefix:
            return nameList
        return [name for name in nameList if name.startswith(prefix)]

    def makeVisible(self, name):
        tl = self.getToplevel(name)
        if not tl:
            raise RuntimeError, "No such window %r" % (name,)
        tl.makeVisible()
    
    def readGeomVisFile(self, fileName=None, doCreate=False):
        """Read toplevel geometry, visibility and state from a file.
        Inputs:
        - fileName: full path to file
        - doCreate: if file does not exist, create a blank one?
        
        File format:
        - Comments (starting with "#") and blank lines are ignored.
        - Data lines have the format:
          name = geometry[, isVisible[, stateDict]]
          where:
          - geometry is a Tk geometry string (size info optional)
          - isVisible is a boolean flag
          - stateDict is json-encoded state dictionary
        """
        fileName = fileName or self.defFileName
        if not fileName:
            raise RuntimeError, "No geometry file specified and no default"
        
        if not os.path.isfile(fileName):
            if doCreate:
                try:
                    outFile = open(fileName, "w")
                    outFile.close()
                except StandardError, e:
                    sys.stderr.write ("Could not create geometry file %r; error: %s\n" % (fileName, RO.StringUtil.strFromException(e)))
                sys.stderr.write ("Created blank geometry file %r\n" % (fileName,))
            else:
                sys.stderr.write ("Geometry file %r does not exist; using default values\n" % (fileName,))
            return

        try:
            inFile = RO.OS.openUniv(fileName)
        except StandardError, e:
            raise RuntimeError, "Could not open geometry file %r; error: %s\n" % (fileName, RO.StringUtil.strFromException(e))
            
        newGeomDict = {}
        newVisDict = {}
        newState = {}
        try:
            for ind, line in enumerate(inFile):
                # if line starts with #, it is a comment, skip it
                if line.startswith("#"):
                    continue
                data = line.split("=", 1)
                if len(data) < 2:
                    # no data on this line; skip it
                    continue
                name = data[0].strip()
                if len(name) == 0:
                    continue

                geomVisList = data[1].split(",", 2)
                if len(geomVisList) == 0:
                    continue

                geom = geomVisList[0].strip()
                if geom:
                    newGeomDict[name] = geom

                if len(geomVisList) > 1:
                    vis = geomVisList[1].strip()
                    if vis:
                        vis = RO.CnvUtil.asBool(vis)
                        newVisDict[name] = vis
                
                if len(geomVisList) > 2:
                    stateDictStr = geomVisList[2].strip()
                    if stateDictStr:
                        try:
                            stateDict = json.loads(stateDictStr)
                            newState[name] = stateDict
                        except Exception, e:
                            sys.stderr.write("Error reading line %d of geometry file %s: %s" % (ind+1, fileName, line))
                            sys.stderr.write("  failed to parse state: %r\n" % (stateDictStr,))
                            sys.stderr.write("  error: %s\n" % (RO.StringUtil.strFromException(e),))

            self.fileGeomDict = newGeomDict
            self.fileVisDict = newVisDict
            self.fileState = newState
        finally:
            inFile.close()
        
    def writeGeomVisFile(self, fileName=None, readFirst = True):
        """Writes toplevel geometry and visiblity info to a file
        that readGeomVisFile can read.
        Comments out entries for windows with default geometry and visibility,
        unless the data was specified in the file.
        
        Inputs:
        - fileName: full path name of geometry file
        - readFirst: read the geometry file first (if it exists) to be sure of having
          a current set of defaults (affects which entries will be commented out)
        """
        fileName = fileName or self.defFileName
        if not fileName:
            raise RuntimeError, "No geometry file specified and no default"
        
        if readFirst and os.path.isfile(fileName):
            self.readGeomVisFile(fileName)

        try:
            outFile = open(fileName, "w")
        except StandardError, e:
            raise RuntimeError, "Could not open geometry file %r; error: %s\n" % (fileName, RO.StringUtil.strFromException(e))
            
        try:
            names = self.getNames()
            names.sort()
            for name in names:
                defGeom = self.defGeomDict.get(name, "")
                defVis = self.defVisDict.get(name, None)
                doSaveState = False
                currState = {}
                isDefaultState = True
                
                tl = self.getToplevel(name)
                if tl:
                    currGeom = tl.getGeometry() or defGeom # getGeometry may return "" if window never displayed
                    currVis = tl.getVisible()
                    doSaveState = tl.getDoSaveState()
                    if doSaveState:
                        currState, isDefaultState = tl.getStateIsDefault()
#                         print "for Toplevel %s: isDefaultState=%s, currState=%s" % (name, isDefaultState, currState)
                else:
                    # Unknown toplevel (e.g. a script window)
                    currGeom = defGeom
                    currVis = False
                isDefaultGeom = currGeom == defGeom
                isDefaultVis = currVis == defVis
                
                # record current values in file dictionaries (to match the file we're writing)
                self.fileGeomDict[name] = currGeom
                self.fileVisDict[name] = currVis
                self.fileState[name] = currState
                
                valueList = [currGeom, str(currVis)]
                if doSaveState:
                    valueList.append(json.dumps(currState))
                    
                # comment out entry if all values are default
                if isDefaultGeom and isDefaultVis and isDefaultState:
                    prefixStr = "# "
                else:
                    prefixStr = ""
                outFile.write("%s%s = %s\n" % (prefixStr, name, ", ".join(valueList)))
        finally:
            outFile.close()


if __name__ == "__main__":
    from RO.Wdg.PythonTk import PythonTk
    root = PythonTk()
    
    testWin = Toplevel(
        title="test window",
        resizable=(False, True),
        geometry = "40x40+150+50"
    )
    l = Tkinter.Label(testWin, text="This is a label")
    l.pack()
    
    def printInfo():
        print "testWin.getGeometry = %r" % (testWin.getGeometry(),)
        print "geometry = %r" % (testWin.geometry())
        print "width, height = %r, %r" % (testWin.winfo_width(), testWin.winfo_height())
        print "req width, req height = %r, %r" % (testWin.winfo_reqwidth(), testWin.winfo_reqheight())
        print ""
    
    b = Tkinter.Button(root, text="Window Info", command=printInfo)
    b.pack()
            
    root.mainloop()
