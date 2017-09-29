
"""Variant on Menubutton that adds callback and severity functionality

History:
2014-05-08 ROwen
2015-03-18 ROwen    Removed Aqua 8.5 width bug workarounds because they are not wanted for Tcl/Tk 8.5.18
"""
__all__ = ['Menubutton']

from six.moves import tkinter
import RO.Constants
from .CtxMenu import CtxMenuMixin


class Menubutton(tkinter.Menubutton, CtxMenuMixin):
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

        tkinter.Menubutton.__init__(self, master = master, **kwArgs)

        CtxMenuMixin.__init__(self, helpURL = helpURL)

    def setEnable(self, doEnable):
        """Enable or disable widget

        Inputs:
        - doEnable: if True enable widget (set state to normal); otherwise set state to disabled

        Warning: if you want the state to be "active" you must set that explicitly.
        """
        if doEnable:
            self["state"] = tkinter.NORMAL
        else:
            self["state"] = tkinter.DISABLED

    def getEnable(self):
        """Return True if widget is enabled, False otherwise

        Enabled is defined as the state is not "disabled" (thus "enabled" or "active").
        """
        return self["state"] != tkinter.DISABLED
