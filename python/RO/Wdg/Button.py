from __future__ import division, print_function
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
2012-11-30 ROwen    Radiobutton bug fix: if using bitmaps the active button was not highlighted, at least on Aqua Tk 8.5.
                    Does no width correction if bitmap is shown.
2015-03-18 ROwen    Bug fix: Radiobutton ignored keyword arguments for configuring the widget.
                    Button: removed special width handling for Aqua Tk as it is neither needed nor wanted
                    for Aqua Tk 8.5.18.
2015-04-02 ROwen    Added a simple workaround for cramped button text in Aqua Tk 8.5.18.
"""
__all__ = ['Button', 'Radiobutton']

import Tkinter
import RO.AddCallback
import RO.Constants
import RO.TkUtil
import CtxMenu
from SeverityMixin import SeverityActiveMixin

class Button(Tkinter.Button, RO.AddCallback.TkButtonMixin, CtxMenu.CtxMenuMixin, SeverityActiveMixin):
    def __init__(self,
        master,
        helpText = None,
        helpURL = None,
        callFunc = None,
        command = None,
        severity = RO.Constants.sevNormal,
    **kwArgs):
        """Creates a new Button.
        
        Inputs:
        - helpText  text for hot help
        - helpURL   URL for longer help
        - callFunc  callback function; the function receives one argument: self.
                    It is called whenever the value changes (manually or via
                    the associated variable being set).
        - command   like callFunc, but the callback receives no arguments (standard Tk behavior)
        - severity  initial severity; one of RO.Constants.sevNormal, sevWarning or sevError
        - all remaining keyword arguments are used to configure the Tkinter Button;
          command is supported, for the sake of conformity, but callFunc is preferred.
        """
        self.helpText = helpText

        if RO.TkUtil.getWindowingSystem() == RO.TkUtil.WSysAqua:
            # buttons with text are too cramped in 8.5.18; add some padding unless it's already been done
            if "text" in kwArgs or "textvariable" in kwArgs:
                kwArgs.setdefault("padx", 10)
                kwArgs.setdefault("pady", 3)

        Tkinter.Button.__init__(self, master = master, **kwArgs)
        
        RO.AddCallback.TkButtonMixin.__init__(self,
            callFunc = callFunc,
            callNow = False,
            command = command,
        )
        
        CtxMenu.CtxMenuMixin.__init__(self, helpURL = helpURL)
        SeverityActiveMixin.__init__(self, severity)
    
    def setEnable(self, doEnable):
        """Enable or disable widget

        Inputs:
        - doEnable: if True enable widget (set state to normal); otherwise set state to disabled

        Warning: if you want the state to be "active" you must set that explicitly.
        """
        if doEnable:
            self["state"] = Tkinter.NORMAL
        else:
            self["state"] = Tkinter.DISABLED
    
    def getEnable(self):
        """Return True if widget is enabled, False otherwise

        Enabled is defined as the state is not "disabled" (thus "enabled" or "active").
        """
        return self["state"] != Tkinter.DISABLED


class Radiobutton(Tkinter.Radiobutton, CtxMenu.CtxMenuMixin, SeverityActiveMixin):
    def __init__(self,
        master,
        helpText = None,
        helpURL = None,
        severity=RO.Constants.sevNormal,
    **kwArgs):
        """Creates a new Button.
        
        Inputs:
        - helpText  text for hot help
        - helpURL   URL for longer help
        - severity  initial severity; one of RO.Constants.sevNormal, sevWarning or sevError
        - all remaining keyword arguments are used to configure the Tkinter Button
        """
        self.helpText = helpText

        Tkinter.Radiobutton.__init__(self, master = master, **kwArgs)
        CtxMenu.CtxMenuMixin.__init__(self, helpURL = helpURL)
        SeverityActiveMixin.__init__(self, severity)
    
