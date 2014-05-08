#!/usr/bin/env python
"""Variant on Menubutton that adds callback and severity functionality and works around some Tk width bugs

History:
2014-05-08 ROwen
"""
__all__ = ['Menubutton']

import Tkinter
import RO.AddCallback
import RO.Constants
import RO.TkUtil
import CtxMenu

class Menubutton(Tkinter.Menubutton, CtxMenu.CtxMenuMixin):
    def __init__(self,
        master,
        helpText = None,
        helpURL = None,
        callFunc = None,
        severity = RO.Constants.sevNormal,
    **kwArgs):
        """Creates a new Menubutton.
        
        Inputs:
        - helpText  text for hot help
        - helpURL   URL for longer help
        - callFunc  callback function; the function receives one argument: self.
                    It is called whenever the value changes (manually or via
                    the associated variable being set).
        - severity  initial severity; one of RO.Constants.sevNormal, sevWarning or sevError
        - all remaining keyword arguments are used to configure the Tkinter Menubutton;
          command is supported, for the sake of conformity, but callFunc is preferred.
        """
        self.helpText = helpText

        # The next few blocks of code work around width bugs in Tk 8.5 for MacOS Aqua
        self._isAqua85 = (RO.TkUtil.getWindowingSystem() == RO.TkUtil.WSysAqua) \
            and RO.TkUtil.getTclVersion().startswith("8.5")

        # configure is NOT called by the Tkinter.Menubutton's constructor,
        # but configure has the code to work around Tk MacOS bugs, so...
        # first construct the object, then call configure with the width
        width = kwArgs.pop("width", None)
        Tkinter.Menubutton.__init__(self, master = master, **kwArgs)
        if width is not None:
            self.configure(width=width)

        # auto width is also broken in Tk 8.5 for MacOS Aqua 
        self._tkVar = kwArgs.get("textvariable")
        if self._isAqua85 and not width and self._tkVar:
            self._tkVar.trace_variable("w", self._patchMacAutoWidth)
            self._patchMacAutoWidth()

        CtxMenu.CtxMenuMixin.__init__(self,
            helpURL = helpURL,
        )
    
    def setEnable(self, doEnable):
        if doEnable:
            self["state"] = "normal"
        else:
            self["state"] = "disabled"
    
    def getEnable(self):
        return self["state"] == "normal"

    def configure(self, argDict=None, **kwArgs):
        """Overridden version of configure that applies a width correction, if necessary

        Notes:
        - configure is called by wdg[item] = value
        - sometimes configure is called with a single positional argument: a dict of items,
            and sometimes it is called with a set of keyword arguments. This code handles both cases.
        """
        if argDict is not None:
            kwArgs.update(argDict)
        if self._isAqua85 and "width" in kwArgs:
            kwArgs["width"] = self._computeCorrectedWidth(
                width = kwArgs["width"],
                hasBitmap = bool(kwArgs.get("bitmap", self["bitmap"])),
                showIndicator = kwArgs.get("indicatoron", self["indicatoron"]),
            )
        Tkinter.Menubutton.configure(self, **kwArgs)

    def _computeCorrectedWidth(self, width, hasBitmap, showIndicator):
        """Compute corrected width to overcome Tcl/Tk bugs

        It's not perfect because menubutton width is very badly screwed up, but it seems to prevent truncation
        """
        if self._isAqua85 and width != 0 and not hasBitmap:
            if showIndicator:
                corrWidth = width + 3
            else:
                corrWidth = width + 2
            return corrWidth
        return width

    def _patchMacAutoWidth(self, *args):
        """Callback function that manually sets width to work around Tcl/Tk bug #3587262
        
        The effect of this bug is that the displayed width may be too narrow in auto mode (width=0)
        on MacOS using Tcl/Tk 8.5. Thus you must only register this
        
        Only register this callback function on aqua Tcl/Tk 8.5
        """
        currVal = self._tkVar.get()
        self["width"] = len(currVal)
