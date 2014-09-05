"""Track the state of a collection of widgets

Intended for use with RO.Wdg.Toplevel in saving and restoring state
"""
import sys
import RO.Alg.GenericCallback
import RO.Constants

__all__ = ["StateTracker"]

class _ItemState(object):
    """Functions for getting and setting item state
    """
    def __init__(self, getFunc, setFunc):
        """Create an _ItemState
        
        Inputs:
        - getFunc: function to get item state; must take no arguments
        - setFunc: function to set item state; must take one argument: the value to set
        """
        self.getFunc = getFunc
        self.setFunc = setFunc


class StateTracker(object):
    """Track the state of a collection of widgets or other items
    
    This is primarily intended for use by ToplevelSet to persist state for Toplevels in a geometry file.
    If you use it for this purpose then the state of each item must be a primitive Python type
    such as a number, string, None, True or False; otherwise the state cannot be persisted.
    """
    def __init__(self, logFunc=None):
        """Create a StateTracker
        
        Inputs:
        - logFunc: a function to call if an item cannot be set or if debugging turned on; must take two arguments:
            - msgStr (positional): the message string
            - severity (by name0: the message severity (an RO.Constants.sev* constant)
            if None then writes to sys.stderr
        - doDebug: if True then print a message for each getState and setState
        """
        if logFunc == None:
            def logFunc(msgStr, severity=RO.Constants.sevNormal):
                sys.stderr.write(msgStr)
        self._logFunc = logFunc
        self._itemDict = {}
    
    def trackWdg(self, name, wdg):
        """Track a widget using getString() and set(value, doCheck=False) methods
        
        Inputs:
        - name: name by which to track this widget
        - wdg: widget to track; if None then uses parent.name
        """
        self.trackItem(
            name = name,
            getFunc = wdg.getString,
            setFunc = RO.Alg.GenericCallback(wdg.set, doCheck=False),
        )
    
    def trackCheckbutton(self, name, wdg):
        """Track a checkbutton widget

        Inputs:
        - name: name by which to track this widget
        - wdg: widget to track; if None then uses parent.name
        """
        self.trackItem(
            name = name,
            getFunc = wdg.getBool,
            setFunc = wdg.setBool,
        )
    
    def trackItem(self, name, getFunc=None, setFunc=None):
        """Track an arbitrary item

        Inputs:
        - name: name by which to track this widget
        - getFunc: function to call to get state
        - setFunc: function to call to set state
        
        Warning: for ToplevelSet to be able to persist the resulting state
        the value returned by getFunc must be a primitive Python type.
        """
        if name in self._itemDict:
            raise RuntimeError("An item named %r is already being tracked" % (name,))

        self._itemDict[name] = _ItemState(
            getFunc = getFunc,
            setFunc = setFunc,
        )
    
    def getState(self):
        """Get the state of all items as a dictionary of name: value
        """
        stateDict = dict((name, item.getFunc()) for name, item in self._itemDict.iteritems())
        return stateDict
    
    def setState(self, stateDict):
        """Set the state of all items as a dictionary of name: value
        
        Unknown and missing keys are ignored.
        If there is an error setting the state of an item a message is printed using logFunc.
        """
        for name, val in stateDict.iteritems():
            item = self._itemDict.get(name)
            if item != None:
                try:
                    item.setFunc(val)
                except Exception, e:
                    self._logFunc("Failed to set %s to %r: %s\n" % (name, val, RO.StringUtil.strFromException(e)), severity=RO.Constants.sevWarning)
 
