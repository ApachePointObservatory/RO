#!/usr/bin/env python
"""Base class for sockets using event-driven programming.

The intention is to work with TCPConnection and all the infrastructure that uses it.
These sockets allow nonblocking event-driven operation:
- Connection and disconnection are done in the background.
- You may begin writing as soon as you start connecting.
- Written data is queued and sent as the connection permits.
- The read and readLine methods are nonblocking.
- You may specify a read callback, which is called when data is available,
  and a state callback, which is called when the connection state changed.

History:
2012-08-10 ROwen    Based on TkSocket.
"""
__all__ = ["BaseSocket", "BaseServer", "NullSocket", "nullCallback"]

import sys
import traceback

def nullCallback(*args, **kwargs):
    """Null callback function
    """
    pass


class Base(object):
    """Base class for BaseSocket and BaseServer
    
    Subclasses may wish to override class variables:
    - _AllStates: a set of states (strings)
    - _DoneStates: a set of states indicating the object is done (e.g. Closed or Failed)
    - _ReadyStates: a set of states indicating the object is ready for use (e.g. Connected)
    """
    def __init__(self,
        state,
        stateCallback = None,
        name = "",
    ):
        """Construct a Base
        
        @param[in] state: initial state
        @param[in] stateCallback: function to call when socket state changes; it receives one argument: this socket;
            if None then no callback
        @param[in] name: a string to identify this object; strictly optional
        """
        self._state = state
        self._reason = ""
        self._stateCallback = stateCallback or nullCallback
        self.name = name

    @property
    def fullState(self):
        """Returns the current state as a tuple:
        - state: as a string
        - reason: the reason for the state ("" if none)
        """
        return (self._state, self._reason)
    
    @property
    def state(self):
        """Returns the current state as a string.
        """
        return self._state
    
    @property
    def isDone(self):
        """Return True if object is fully closed (due to request or failure)
        """
        return self._state in self._DoneStates
    
    @property
    def isReady(self):
        """Return True if object is ready, e.g. socket is connected or server is listening
        """
        return self._state in self._ReadyStates
    
    @property
    def didFail(self):
        """Return True if object failed, e.g. connection failed
        """
        return self._state in self._FailedStates
    
    def setStateCallback(self, callFunc=nullCallback):
        """Set the state callback function (replacing the current one).
        
        Inputs:
        - callFunc: the callback function, or None if none wanted
                    The function is sent one argument: this Socket
        """
        self._stateCallback = callFunc or nullCallback
    
    def setName(self, newName):
        """Set socket name
        """
        self.name = newName

    def _clearCallbacks(self):
        """Clear any callbacks added by this class.
        """
        self._stateCallback = nullCallback

    def _setState(self, newState, reason=None):
        """Change the state.
        
        Inputs:
        - newState: the new state
        - reason: an explanation (None to leave alone)
        """
#         print "%s._setState(newState=%s, reason=%s)" % (newState, reason)
        if self.isDone:
            raise RuntimeError("Already done; cannot change state")

        self._state = newState
        if reason is not None:
            self._reason = str(reason)
        
        stateCallback = self._stateCallback # make a temporary copy to run after clearing other callbacks
        if self.isDone:
            try:
                self._clearCallbacks()
            except Exception, e:
                sys.stderr.write("%s failed to clear callbacks: %s\n" % (self, e,))
                traceback.print_exc(file=sys.stderr)
        
        try:
            stateCallback(self)
        except Exception, e:
            sys.stderr.write("%s state callback %s failed: %s\n" % (self, self._stateCallback, e,))
            traceback.print_exc(file=sys.stderr)

    def _getArgStr(self):
        """Return main arguments as a string, for __str__
        """
        return "name=%r" % (self.name)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self._getArgStr())


class BaseSocket(Base):
    """Base class for event-driven communication sockets.
    """
    Connecting = "Connecting"
    Connected = "Connected"
    Closing = "Closing"
    Failing = "Failing"
    Closed = "Closed"
    Failed = "Failed"
    
    _AllStates = set((
        Connecting,
        Connected,
        Closing,
        Failing,
        Closed,
        Failed,
    ))
    _DoneStates = set((Closed, Failed))
    _ReadyStates = set((Connected,))
    _FailedStates = set((Failed,))
        
    StateStrMaxLen = 0
    for _stateStr in _AllStates:
        StateStrMaxLen = max(StateStrMaxLen, len(_stateStr))
    del(_stateStr)
    
    def __init__(self,
        state = Connected,
        readCallback = None,
        stateCallback = None,
        name = "",
    ):
        """Construct a BaseSocket
        
        Arguments:
        - state: initial state
        - readCallback: function to call when data is read; it receives one argument: this socket
        - stateCallback: function to call when socket state changes; it receives one argument: this socket
        - name: a string to identify this socket; strictly optional
        """
        self._readCallback = readCallback or nullCallback
        Base.__init__(self,
            state = state,
            stateCallback = stateCallback or nullCallback,
            name = name,
        )

    def read(self, nChar=None):
        """Return up to nChar characters; if nChar is None then return all available characters.
        """
        raise NotImplementedError()

    def readLine(self, default=None):
        """Read one line of data.
        Do not return the trailing newline.
        If a full line is not available, return default.
        
        Inputs:
        - default   value to return if a full line is not available
                    (in which case no data is read)
        
        Raise RuntimeError if the socket is not connected.
        """
        raise NotImplementedError()
    
    def setReadCallback(self, callFunc=None):
        """Set the read callback function (replacing the current one).
        
        Inputs:
        - callFunc: the callback function, or nullCallback if none wanted.
                    The function is sent one argument: this Socket
        """
        self._readCallback = callFunc or nullCallback
    
    def write(self, data):
        """Write data to the socket. Does not block.
        
        Safe to call as soon as you call connect, but of course
        no data is sent until the connection is made.
        
        Raises UnicodeError if the data cannot be expressed as ascii.
        Raises RuntimeError if the socket is not connecting or connected.
        If an error occurs while sending the data, the socket is closed,
        the state is set to Failed and _reason is set.
        """
        raise NotImplementedError()
    
    def writeLine(self, data):
        """Write a line of data terminated by standard newline
        (which for the net is \r\n, but the socket's auto newline
        translation takes care of it).
        """
        raise NotImplementedError()

    def close(self, isOK=True, reason=None):
        """Start closing the socket.
        
        Does nothing if the socket is already closed or failed.
        
        Inputs:
        - isOK: if True, mark state as Closed, else Failed
        - reason: a string explaining why, or None to leave unchanged;
            please specify if isOK is false.
        """
#         print "%s.close(isOK=%r, reason=%r)" % (self, isOK, reason)
        if self.isDone:
            return

        if isOK:
            self._setState(self.Closing, reason)
        else:
            self._setState(self.Failing, reason)

        self._basicClose()
    
    def _basicClose(self):
        """Start closing the socket.
        """
        raise NotImplementedError()

    def _clearCallbacks(self):
        """Clear any callbacks added by this class.
        """
        Base._clearCallbacks(self)
        self._readCallback = nullCallback


class BaseServer(Base):
    """Base class for a socket server
    """
    Starting = "Starting"
    Listening = "Listening"
    Closing = "Closing"
    Failing = "Failing"
    Closed = "Closed"
    Failed = "Failed"
    
    _AllStates = set((
        Starting,
        Listening,
        Closing,
        Failing,
        Closed,
        Failed,
    ))
    _DoneStates = set((Closed, Failed))
    _ReadyStates = set((Listening,))
    _FailedStates = set((Failed,))

    def __init__(self,
        connCallback,
        state = Starting,
        stateCallback = None,
        sockReadCallback = None,
        sockStateCallback = None,
        name = "",
    ):
        """Construct a socket server
        
        Inputs:
        - connCallback: function to call when a client connects; it receives the following arguments:
                    - sock, a BaseSocket
        - stateCallback: a function to call when the server changes state
        - sockReadCallback: function to call when a socket receives data
        - sockStateCallback: function to call when a socket changes state
        - name: a string to identify this server; strictly optional
        - state: initial state
        """
        self._connCallback = connCallback or nullCallback
        self._sockReadCallback = sockReadCallback or nullCallback
        self._sockStateCallback = sockStateCallback or nullCallback
        Base.__init__(self,
            state = state,
            stateCallback = stateCallback or nullCallback,
            name = name,
        )        

    def _basicClose(self):
        """Shut down the server.
        """
        raise NotImplementedError()
    
    def close(self, isOK=True, reason=None):
        """Start closing the server.
        
        Does nothing if the socket is already closed or failed.
        
        Inputs:
        - isOK: if True, mark state as Closed, else Failed
        - reason: a string explaining why, or None to leave unchanged;
            please specify if isOK is false.
        """
#         print "%s.close(isOK=%r, reason=%r)" % (self, isOK, reason)
        if self.isDone:
            return

        if isOK:
            self._setState(self.Closing, reason)
        else:
            self._setState(self.Failing, reason)

        self._basicClose()

    def _basicClose(self):
        """Start closing the socket.
        """
        raise NotImplementedError()
    
    def _clearCallbacks(self):
        """Clear any callbacks added by this class.
        Called just after the socket is closed.
        """
        Base._clearCallbacks(self)
        self._connCallback = nullCallback
        self._sockReadCallback = nullCallback
        self._sockStateCallback = nullCallback


class NullSocket(BaseSocket):
    """Null connection.
    Forbids read, write and setting a new state callback.
    Close is OK and the state is always Closed.
    """
    def __init__ (self):
        BaseSocket.__init__(self,
            state = self.Closed,
        )
        self._reason = "This is an instance of NullSocket"

    def read(self, *args, **kargs):
        raise RuntimeError("Cannot read from null socket")
        
    def readLine(self, *args, **kargs):
        raise RuntimeError("Cannot readLine from null socket")

    def write(self, astr):
        raise RuntimeError("Cannot write %r to null socket" % astr)

    def writeLine(self, astr):
        raise RuntimeError("Cannot writeLine %r to null socket" % astr)
