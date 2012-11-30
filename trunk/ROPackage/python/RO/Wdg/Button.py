#!/usr/bin/env python
"""Variants on buttons that add help.

History:
2003-04-24 ROwen
2003-06-12 ROwen    Added Radiobutton.
2003-08-04 ROwen    Added addCallback; modified to use RO.AddCallback.
2004-08-11 ROwen    Define __all__ to restrict import.
2004-09-14 ROwen    Tweaked the imports.
2005-06-15 ROwen    Added severity support. Unfortunately, for Button
                    it has no visible effect on MacOS X Aqua.
2012-11-30 ROwen    Work around Aqua Tk 8.5 bug for Radiobutton: if width specified it is too narrow
                    (the fix will need modification if this bug is also present on Aqua Tk 8.6)
"""
__all__ = ['Button', 'Radiobutton']

import Tkinter
import RO.AddCallback
import RO.Constants
import RO.TkUtil
import CtxMenu
from SeverityMixin import SeverityActiveMixin

class Button (Tkinter.Button, RO.AddCallback.TkButtonMixin, CtxMenu.CtxMenuMixin,
    SeverityActiveMixin):
    def __init__(self,
        master,
        helpText = None,
        helpURL = None,
        callFunc = None,
        severity = RO.Constants.sevNormal,
    **kargs):
        """Creates a new Button.
        
        Inputs:
        - helpText  text for hot help
        - helpURL   URL for longer help
        - callFunc  callback function; the function receives one argument: self.
                    It is called whenever the value changes (manually or via
                    the associated variable being set).
        - severity  initial severity; one of RO.Constants.sevNormal, sevWarning or sevError
        - all remaining keyword arguments are used to configure the Tkinter Button;
          command is supported, for the sake of conformity, but callFunc is preferred.
        """
        self.helpText = helpText

        Tkinter.Button.__init__(self, master = master, **kargs)
        
        RO.AddCallback.TkButtonMixin.__init__(self, callFunc, False, **kargs)
        
        CtxMenu.CtxMenuMixin.__init__(self,
            helpURL = helpURL,
        )
        SeverityActiveMixin.__init__(self, severity)
    
    def setEnable(self, doEnable):
        if doEnable:
            self["state"] = "normal"
        else:
            self["state"] = "disabled"
    
    def getEnable(self):
        return self["state"] == "normal"


class Radiobutton (Tkinter.Radiobutton, CtxMenu.CtxMenuMixin, SeverityActiveMixin):
    def __init__(self,
        master,
        helpText = None,
        helpURL = None,
        severity=RO.Constants.sevNormal,
    **kargs):
        """Creates a new Button.
        
        Inputs:
        - helpText  text for hot help
        - helpURL   URL for longer help
        - severity  initial severity; one of RO.Constants.sevNormal, sevWarning or sevError
        - all remaining keyword arguments are used to configure the Tkinter Button
        """
        self.helpText = helpText

        Tkinter.Radiobutton.__init__(self, master = master)
        self.configure(kargs) # call overridden configure to fix width, if necessary
        CtxMenu.CtxMenuMixin.__init__(self,
            helpURL = helpURL,
        )
        SeverityActiveMixin.__init__(self, severity)
    
    def configure(self, argDict=None, **kargs):
        """Overridden version of configure that applies a width correction, if necessary

        Notes:
        - configure is called by wdg[item] = value
        - sometimes configure is called with a single positional argument: a dict of items,
            and sometimes it is called with a set of keyword arguments. This code handles both cases.
        - configure is NOT called by the widget's constructor, so you must call configure with your desired width
            after constructing the widget, rather than passing width to the widget's constructor
        """
        if argDict is not None:
            kargs.update(argDict)
        if "width" in kargs:
            initialWidth = kargs["width"]
            kargs["width"] = self._computeCorrectedWidth(
                width = kargs["width"], 
                showIndicator = kargs.get("indicatoron", self["indicatoron"]),
            )
        Tkinter.Radiobutton.configure(self, **kargs)
    
    def _computeCorrectedWidth(self, width, showIndicator):
        """Compute corrected width to overcome Tcl/Tk bug
        """
        if (width != 0) \
            and (RO.TkUtil.getWindowingSystem() == RO.TkUtil.WSysAqua) \
            and RO.TkUtil.getTclVersion().startswith("8.5"):
            return width + 4
        return width
