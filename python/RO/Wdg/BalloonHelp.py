#!/usr/bin/env python
"""Simple implementation of pop-up help.

Call enableBalloonHelp to activate help for all widgets that have a helpText attribute.

Help is shown if the mouse is left over a control or moved within a control

History:
2004-08-11 ROwen    Define __all__ to restrict import.
2012-07-10 ROwen    Improve the behavior: the help doesn't flicker if the mouse is moved within a control.
                    Added isShowing property.
                    Modified to use RO.TkUtil.Timer.
                    Removed use of update_idletasks.
"""
__all__ = ['enableBalloonHelp']

import Tkinter
from RO.TkUtil import Timer

_HelpObj = None

class _BalloonHelp:
    """Show balloon help for any widget that has a helpText attribute
    
    Help is shown delayMS after the mouse enters a widget or moves within a widget.
    If help was showing within 0.6 sec of moving to a new widget then the help
    for the new widget is shown immediately.
    
    Help is hidden if the user clicks or types. However, the help timer is started again
    if the mouse moves within the widget.
    """
    def __init__(self, delayMS = 600):
        """Construct a _BalloonHelp
        
        Inputs:
        - delayMS: delay time before help is shown
        """
        self._isShowing = False
        self._delayMS = delayMS
        self._showTimer = Timer()
        self._leaveTimer = Timer()
        self._msgWin = Tkinter.Toplevel()
        self._msgWin.overrideredirect(True)
        self._msgWdg = Tkinter.Message(self._msgWin, bg="light yellow")
        self._msgWdg.pack()
        self._msgWin.withdraw()
        self._msgWdg.bind_all('<Motion>', self._start)
        self._msgWdg.bind_all('<Leave>', self._leave)
        self._msgWdg.bind_all('<ButtonPress>', self._stop)
        self._msgWdg.bind_all('<KeyPress>', self._stop)
        self._msgWdg.bind_all('<Tab>', self._stop, add=True)
        self._msgWin.bind("<Configure>", self._configure)
    
    def _configure(self, evt=None):
        """Callback for window Configure event
        
        Using this flickers less than calling this from show (even using a short time delay).
        Note: using self._isShowing is paranoia; the <Configure> event is only triggered
        by show (which changes the message).
        """
        if self._isShowing:
            self._msgWin.tkraise()
            self._msgWin.deiconify()
    
    def _leave(self, evt=None):
        """Mouse has left a widget; start the leave timer if help is showing and stop showing help
        """
        if self._isShowing:
            self._leaveTimer.start(0.6, self._leaveDone)
        self._stop()
    
    def _leaveDone(self):
        """No-op for leave timer; can add a print statement for diagnostics
        """
        pass

    def _start(self, evt):
        """Start a timer to show the help in a bit.
        
        If the help window is already showing, redisplay it immediately
        """
        if self._isShowing:
            return
        self._isShowing = True

        try:
            if evt.widget.helpText and not self._showTimer.isActive:
                # widget has help and the show timer is not already running
                justLeft = self._leaveTimer.cancel()
                if justLeft:
                    # recently left another widget while showing help; show help for this widget right away
                    delay = 0.001
                else:
                    # not recently showing help; wait the usual time to show help
                    delay = self._delayMS / 1000.0
                self._showTimer.start(delay, self._show, evt)
        except AttributeError:
            pass
    
    def _show(self, evt):
        """Show help
        """
        self._isShowing = True
        x, y = evt.x_root, evt.y_root
        self._msgWin.geometry("+%d+%d" % (x+10, y+10))
        self._msgWdg["text"] = evt.widget.helpText
    
    def _stop(self, evt=None):
        """Stop the timer and hide the help
        """
        self._isShowing = False
        self._showTimer.cancel()
        self._msgWin.withdraw()
        

def enableBalloonHelp(delayMS = 1000):
    """Enable balloon help application-wide
    """
    global _HelpObj
    if _HelpObj:
        _HelpObj._delayMS = delayMS
    else:
        _HelpObj = _BalloonHelp(delayMS)


if __name__ == '__main__':
    import OptionMenu
    root = Tkinter.Tk()
    
    l0 = Tkinter.Label(text="Data")
    l0.grid(row=0, column=0, sticky="e")
    l0.helpText = "Help for the Data label"
    e0 = Tkinter.Entry(width=10)
    e0.helpText = "A really long help string describing the data entry widget"
    e0.grid(row=0, column=1)
    l1 = Tkinter.Label(text="No Help")
    l1.grid(row=1, column=0)
    e1 = Tkinter.Entry(width=10)
    e1.grid(row=1, column=1)
    l2 = Tkinter.Label(text="Option Menu")
    l2.helpText = "Help for the option menu label"
    l2.grid(row=2, column=0)
    m2 = OptionMenu.OptionMenu(root,
        items = ("Item 1", "Item 2", "Etc"),
        defValue = "Item 1",
        helpText = "Help for the menu button",
    )
    m2.grid(row=2, column=1)

    ph = enableBalloonHelp()
    
    root.mainloop()
