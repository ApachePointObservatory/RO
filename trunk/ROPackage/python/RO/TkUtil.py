#!/usr/bin/env python
"""Tkinter utilities

History:
2004-10-08 ROwen
2004-10-12 ROwen    Modified getWindowingSystem to handle versions of Tk < ~8.4
2005-06-17 ROwen    Added getButtonNumbers.
2005-07-07 ROwen    Added TclFunc
2005-08-24 ROwen    Expanded the docstring for TclFunc and made the tcl name a bit clearer.
2005-08-25 ROwen    Removed useless __del__ from TclFunc and updated the documentation.
2005-09-12 ROwen    Added EvtNoProp.
2006-10-25 ROwen    Added addColors (based on scaleColor from RO.Wdg.WdgPrefs).
                    Modified colorOK to use winfo_rgb.
2010-05-04 ROwen    Added Geometry, including the ability to constrain a window's geometry to fit on screen.
2010-05-21 ROwen    Bug fix: Geometry.toTkStr could include extent when it shouldn't.
2010-07-20 ROwen    Added Timer class.
"""
__all__ = ['addColors', 'colorOK', 'EvtNoProp', 'getWindowingSystem', 'TclFunc', 'Geometry',
    'WSysAqua', 'WSysX11', 'WSysWin']

import re
import sys
import traceback
import Tkinter
import RO.OS

# windowing system constants
WSysAqua = "aqua"
WSysX11 = "x11"
WSysWin = "win32"

# internal globals
g_tkWdg = None
g_winSys = None

def addColors(*colorMultPairs):
    """Add colors or scale a color.
    
    Inputs:
    - A list of one or more (color, mult) pairs.
    
    Returns sum of (R, G, B) * mult for each (color, mult) pair,
    with R, G, and B individually limited to range [0, 0xFFFF].
    """
    netRGB = [0, 0, 0]
    for color, mult in colorMultPairs:
        colorRGB = _getTkWdg().winfo_rgb(color)
        netRGB = [netRGB[ii] + (mult * colorRGB[ii]) for ii in range(3)]
    truncRGB = [max(min(int(val), 0xFFFF), 0) for val in netRGB]
    retColor = "#%04x%04x%04x" % tuple(truncRGB)
    #print "mixColors(%r); netRGB=%s; truncRGB=%s; retColor=%r" % (colorMultPairs, netRGB, truncRGB, retColor)
    return retColor

def colorOK(colorStr):
    """Return True if colorStr is a valid tk color, False otherwise.
    """
    tkWdg = _getTkWdg()

    try:
        tkWdg.winfo_rgb(colorStr)
    except Tkinter.TclError:
        return False
    return True

class EvtNoProp(object):
    """Function wrapper that prevents event propagation.
    Input: function to bind
    """
    def __init__(self, func):
        self.func = func
    def __call__(self, *args, **kargs):
        self.func(*args, **kargs)
        return "break"

def getButtonNumbers():
    """Return the button numbers corresponding to
    the left, middle and right buttons.
    """
    winSys = getWindowingSystem()
    if winSys == WSysAqua:
        return (1, 3, 2)
    else:
        return (1, 2, 3)

def getWindowingSystem():
    """Return the Tk window system.
    
    Returns one of:
    - WSysAqua: the MacOS X native system
    - WSysX11: the unix windowing system
    - WSysWin: the Windows windowing system
    Other values might also be possible.
    
    Please don't call this until you have started Tkinter with Tkinter.Tk().
    
    Warning: windowingsystem is a fairly recent tk command;
    if it is not available then this code does its best to guess
    but will not guess aqua.
    """
    global g_winSys
    
    if not g_winSys:
        tkWdg = _getTkWdg()
        try:
            g_winSys = tkWdg.tk.call("tk", "windowingsystem")
        except Tkinter.TclError:
            # windowingsystem not supported; take a best guess
            if RO.OS.PlatformName == "win":
                g_winSys = "win32"
            else:
                g_winSys = "x11"

    return g_winSys

#class TkAdapter:
    #_tkWdg = None
    #def __init__(self):
        #if self._tkWdg == None:
            #self._tkWdg = self._getTkWdg()
        #self.funcDict = {}
    
    #def after(*args):
        #self._tkWdg.after(*args)

    #def register(self, func):
        #"""Register a function as a tcl function.
        #Returns the name of the tcl function.
        #Be sure to deregister the function when done
        #or delete the TkAdapter
        #"""
        #funcObj = TclFunc(func)
        #funcName = funcObj.tclFuncName
        #self.funcDict[funcName] = funcObj
        #return funcName
    
    #def deregister(self, funcName):
        #"""Deregister a tcl function.

        #Raise KeyError if function not found.
        #"""
        #func = self.funcDict.pop(funcName)
        #func.deregister()
    
    #def eval(self, *args):
        #"""Evaluate an arbitrary tcl expression and return the result"""
        #return self._tkWdg.tk.eval(*args)

    #def call(self, *args):
        #"""Call a tcl function"""
        #return self._tkWdg.tk.call(*args)

class TclFunc:
    """Register a python function as a tcl function.
    Based on Tkinter's _register method (which, being private,
    I prefer not to use explicitly).
    
    If the function call fails, a traceback is printed.
    
    Please call deregister when you no longer
    want the tcl function to exist.
    """
    tkApp = None
    def __init__(self, func, debug=False):
        if self.tkApp == None:
            self.tkApp = _getTkWdg().tk
        self.func = func
        self.tclFuncName = "pyfunc%s" % (id(self),)
        self.debug = bool(debug)
        try:
            self.tclFuncName += str(func.__name__)
        except AttributeError:
            pass
        if self.debug:
            print "registering tcl function %s for python function %s" % (self.tclFuncName, func)
        self.tkApp.createcommand(self.tclFuncName, self)
    
    def __call__(self, *args):
        try:
            self.func(*args)
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception, e:
            sys.stderr.write("tcl function %s failed: %s\n" % (self.tclFuncName, e))
            traceback.print_exc(file=sys.stderr)
        
    def deregister(self):
        """Deregister callback and delete reference to python function.
        Safe to call if already deregistered.
        """
        if self.debug:
            print "%r.deregister()" % (self,)
        if not self.func:
            if self.debug:
                print "already deregistered"
            return
        try:
            self.tkApp.deletecommand(self.tclFuncName)
        except Tkinter.TclError, e:
            if self.debug:
                print "deregistering failed: %r" % (e,)
            pass
        self.func = None
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.tclFuncName)
    
    def __str__(self):
        return self.tclFuncName

class Geometry(object):
    """A class representing a tk geometry
    
    Fields include the following two-element tuples:
    - offset: x,y offset of window relative to screen; see also offsetFlipped
    - offsetFlipped: is the meaning of x,y offset flipped?
        if False (unflipped) then offset is the distance from screen top/left to window top/left
        if True (flipped) offset is the distance from window bottom/right to screen bottom/right
    - extent: x,y extent; always positive or (None, None) if extent is unknown

    System constants:
    - minCorner: minimum visible offset position (platform-dependent)
    - screenExtent: x,y extent of all screens put together
        (if the screens are not the same size and arranged side by side
        then the area will include pixels that are not visible)
    
    WARNING: on some platforms offsetFlipped < 0 is not handled properly.
    In particular on Mac OS X with Tk 8.4:
    - the offset is actually relative to the top or right offset of the window,
        which is dead wrong
    - setting the geometry for a window with ngeative offset offset may simply not work,
        resulting in a geometry that is not what you asked for
        (I have particularly seen this for windows nearly as large as the screen)
    That is why the constrainToGeomStr method always returns a tk geometry string with positive corners.
    """
    if RO.OS.PlatformName == "mac":
        minCorner = (0, 22)
    else:
        minCorner = (0, 0)
    _root = None
    _geomRE = re.compile(
        r"((?P<width>\d+)x(?P<height>\d+))?(?P<xsign>[+-])(?P<x>[-]?\d+)(?P<ysign>[+-])(?P<y>[-]?\d+)$",
        re.IGNORECASE)
        
    def __init__(self, offset, offsetFlipped, extent):
        """Create a new Geometry
        
        Inputs (each is a sequence of two values):
        - offset: x,y offset of window relative to screen; see also offsetFlipped
        - offsetFlipped: is the meaning of x,y offset flipped?
            if False (unflipped) then offset is the distance from screen top/left to window top/left
            if True (flipped) offset is the distance from window bottom/right to screen bottom/right
        - extent: x,y extent; you may specify None or (None, None) if the extent is unknown;
            however, you may not specify an integer for one axis and None for the other

        raise RuntimeError if any input does not have two elements (except that extent may be None)
        """
        if len(offset) != 2:
            raise RuntimeError("offset=%r does not have two values" % (offset,))
        self.offset = tuple(int(val) for val in offset)

        if len(offsetFlipped) != 2:
            raise RuntimeError("offsetFlipped=%r does not have two values" % (offsetFlipped,))
        self.offsetFlipped = tuple(bool(val) for val in offsetFlipped)

        if extent == None:
            self.extent = (None, None)
        else:
            if len(extent) != 2:
                raise RuntimeError("extent=%r does not have two values" % (extent,))
            if None in extent:
                self.extent = (None, None)
            else:
                self.extent = tuple(int(val) for val in extent)

    @classmethod
    def fromTkStr(cls, geomStr):
        """Create a Geometry from a tk geometry string
        
        Inputs:
        - geomStr: tk geometry string
        """
        match = cls._geomRE.match(geomStr)
        if not match:
            raise RuntimeError("Could not parse geomStr string %r" % (geomStr,))

        groupDict = match.groupdict()

        return cls(
            offset = tuple(groupDict[name] for name in ("x", "y")),
            offsetFlipped = tuple(cls._flippedFromChar(groupDict[name]) for name in ("xsign", "ysign")),
            extent = tuple(groupDict[name] for name in ("width", "height")),
        )

    def constrained(self, constrainExtent=True, defExtent=50):
        """Return a geometry that is constrain to lie entirely within the screen(s)

        Inputs:
        - constrainExtent: if True then the extent and offset position are both constrained
            else only the offset position is constrained
        - defExtent: the extent to assume if the extent is not known; ignored if the extent is known
        
        Returns:
        - a geometry string (not a Geometry, but you can trivially convert it to one)
        
        Warnings:
        - If the user has multiple screens and they are not the same size or lined up side by side
          then the resulting geometry may not be entirely visible, or even partially visiable.
        """
        constrainedOffset = []
        constrainedExtent = []
        for ii in range(2):
            extent_ii = self.extent[ii]
            if extent_ii == None:
                extent_ii = defExtent
            corner_ii = self.offset[ii]
            minCorner_ii = self.minCorner[ii]
            usableScreenExtent_ii = self.screenExtent[ii] - minCorner_ii
            
            tooLarge_ii = extent_ii > usableScreenExtent_ii
            
            if tooLarge_ii and constrainExtent:
                extent_ii = usableScreenExtent_ii
            
            if self.offsetFlipped[ii]:
                # offset is distance from bottom/right of window to bottom/right of screen
                # to avoid tk bugs, the constrained result will NOT use this convention
                corner_ii = usableScreenExtent_ii - (corner_ii + extent_ii)
    
            if tooLarge_ii:
                corner_ii = minCorner_ii
            elif corner_ii < minCorner_ii:
                corner_ii = minCorner_ii
            elif extent_ii + corner_ii > usableScreenExtent_ii:
                # off lower or right edge
                corner_ii = usableScreenExtent_ii - extent_ii
            constrainedOffset.append(corner_ii)
            constrainedExtent.append(extent_ii)

        if not self.hasExtent:
            constrainedExtent = (None, None)
        return type(self)(offset=constrainedOffset, offsetFlipped=(False, False), extent=constrainedExtent)

    @property
    def hasExtent(self):
        return None not in self.extent
        
    @property
    def screenExtent(self):
        if not self._root:
            self._root = _getTkWdg().winfo_toplevel()
        return self._root.wm_maxsize()

    def toTkStr(self, includeExtent=None):
        """Return the geometry as a tk geometry string
        
        Inputs:
        - includeExtent: include extent information? One of:
            - None: include if available, else omit
            - True: must include it; raise RuntimeError if extent information unavailable
            - False: exclude extent information
        """
        posStr = "%s%d%s%d" % (
            self._signStrFromValue(self.offsetFlipped[0]), self.offset[0],
            self._signStrFromValue(self.offsetFlipped[1]), self.offset[1])

        if includeExtent == None:
            includeExtent = self.hasExtent

        if includeExtent:
            if not self.hasExtent:
                raise RuntimeError("includeExent=True but extent information unavailable")
            return "%dx%d%s" % (self.extent[0], self.extent[1], posStr)

        return posStr

    def __str__(self):
        return self.toTkStr()

    def __repr__(self):
        return "%s(\"%s\")" % (type(self).__name__, self.toTkStr())

    @staticmethod
    def _intFromStr(val):
        if val == None:
            return val
        return int(val)

    @staticmethod
    def _flippedFromChar(valStr):
        if valStr == "-":
            return True
        elif valStr == "+":
            return False
        else:
            raise RuntimeError("Invalid valStr=%r must be \"+\" or \"-\"" % (valStr,))

    @staticmethod
    def _signStrFromValue(val):
        if val < 0:
            return "-"
        else:
            return "+"


class Timer(object):
    """A restartable one-shot timer
    """
    def __init__(self, sec=None, callFunc=None, *args):
        """Start or set up a one-shot timer

        Inputs:
        - sec: interval, in seconds (float); if omitted then the timer is not started
        - callFunc: function to call when timer fires
        *args: arguments for callFunc
        """
        self._tkWdg = _getTkWdg()
        self._timerID = None
        if sec != None:
            self.startTimer(sec, callFunc, *args)
    
    def start(self, sec, callFunc, *args):
        """Start or restart the timer, cancelling a pending timer if present
        
        Inputs:
        - sec: interval, in seconds (float)
        - callFunc: function to call when timer fires
        *args: arguments for callFunc
        """
        self.cancel()
        self._timerID = self._tkWdg.after(int(0.5 + (1000.0 * sec)), callFunc, *args)

    def cancel(self):
        """Cancel the timer; a no-op if the timer is not active"""
        if self._timerID:
            self._tkWdg.after_cancel(self._timerID)


def _getTkWdg():
    """Return a Tk widget"""
    global g_tkWdg
    if not g_tkWdg:
        g_tkWdg = Tkinter.Frame()
    return g_tkWdg

if __name__ == "__main__":
    import Tkinter
    root = Tkinter.Tk()

    def setGeometry(geomStrList):
        if not geomStrList:
            root.quit()
            return
        geomStr = geomStrList.pop()
        geomObj = Geometry.fromTkStr(geomStr)
        constrainedGeom = geomObj.constrained()
        print "geomStr=%s; constrainedGeomStr=%s" % (geomStr, constrainedGeom)
        root.geometry(constrainedGeom.toTkStr())
        root.after(2000, setGeometry, geomStrList)
        
    setGeometry([
        "20000x200+0+0",
        "200x20000-0-0",
        "20000x20000-50+50",
        "-50+50",
        "+50+50",
    ])
    root.mainloop()
