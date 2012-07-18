"""Twisted one-shot timer

Requires a running twisted reactor.

History:
2012-07-13 ROwen    Copied from opscore, but with active() replaced by isActive.
"""
import twisted.internet.reactor

_reactor = twisted.internet.reactor

class Timer(object):
    """A restartable one-shot timer
    """
    def __init__(self, sec=None, callFunc=None, *args, **keyArgs):
        """Start or set up a one-shot timer

        Inputs:
        - sec: interval, in seconds (float); if omitted then the timer is not started
        - callFunc: function to call when timer fires
        *args: arguments for callFunc
        **keyArgs: keyword arguments for callFunc; must not include "sec" or "callFunc"
        """
        if sec != None:
            self._timer = _reactor.callLater(sec, callFunc, *args, **keyArgs)
        else:
            self._timer = None
    
    def start(self, sec, callFunc, *args, **keyArgs):
        """Start or restart the timer, cancelling a pending timer if present
        
        Inputs:
        - sec: interval, in seconds (float)
        - callFunc: function to call when timer fires
        *args: arguments for callFunc
        **keyArgs: keyword arguments for callFunc; must not include "sec" or "callFunc"
        """
        self.cancel()
        self._timer = _reactor.callLater(sec, callFunc, *args, **keyArgs)

    def cancel(self):
        """Cancel the timer; a no-op if the timer is not active
        
        Return True if timer was running, False otherwise
        """
        if self.isActive:
            self._timer.cancel()
            return True
        return False

    @property
    def isActive(self):
        """Return True if the timer is active"""
        return (self._timer is not None) and self._timer.active()
