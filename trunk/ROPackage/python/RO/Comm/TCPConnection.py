#!/usr/bin/env python -i
"""Reconnectable versions of TCPSocket.

All permit disconnection and reconnection and the base class offers support for
authorization and line-oriented output.

Requirements:
- Tkinter or Twisted framework; see RO.Comm.Generic.

History:
2002-11-22 R Owen: first version with history. Moved to RO.Comm
    and modified to use TkSocket sockets. This fixed a pitfall
    (it was not safe to close the socket if a read handler
    was present) and socket writes are done in a background thread
    and so no longer block.
2002-12-13 ROwen    Moved isConnected from VMSTelnet to TCPConnection.
2003-02-27 ROwen    Added setStateCallback; added connection state.
    Overhauled connection subroutine handling: you can now have multiple
    connection subroutines, they receive the new connection state variable
    and an explanatory message.
    Overhauled VMSTelnet to use this instead of printing negotation status directly.
2003-07-18 ROwen    Renamed subroutine to function, for consistency with other code;
    improved doc strings (including adding a doc string to NullConnection).
2003-10-13 ROwen    Major overhaul to match new TkSocket and simplify subclasses.
2003-11-19 ROwen    Bug fix: reason was not always a string; modified _setState
                    to cast it to a string.
2003-12-04 ROwen    Modified to only call the state callback when the state
                    or reason changes.
                    Changed doCall to callNow in addStateCallback,
                    for consistency with other addCallback functions.
2004-05-18 ROwen    Stopped importing string, Tkinter, RO.Alg and RO.Wdg; they weren't used.
2004-07-13 ROwen    Modified for overhauled TkSocket.
2004-09-14 ROwen    Importing socket module but not using it.
2004-10-12 ROwen    Corrected documentation for addReadCallback and addStateCallback.
2005-06-08 ROwen    Changed TCPConnection to a new-style class.
2005-08-10 ROwen    Modified for TkSocket state constants as class const, not module const.
2005-08-11 ROwen    Added isDone and getProgress methods.
2008-01-23 ROwen    Removed getProgress method. It was clumsy and better handled by the user.
                    Modified connect to raise RuntimeError if:
                    - host and self.host are both blank. Formerly it disconnected the socket.
                    - already connected. Formerly it disconnected (without waiting for that to finish)
                    and then connected. That was two operations, which made it hard to track completion.
2008-01-25 ROwen    Tweaked connect to raise RuntimeError if connecting or connected (not just connected).
2008-02-13 ROwen    Added mayConnect method.
2010-06-28 ROwen    Removed unused import (thanks to pychecker).
2012-07-16 ROwen    Added support for Twisted framework.
                    You must now call RO.Comm.Generic.setFramework before importing this module.
                    Added name attribute to TCPConnection.
"""
import sys
from RO.Comm.BaseSocket import NullSocket
from RO.Comm.Generic import TCPSocket

class TCPConnection(object):
    """A TCP Socket with the ability to disconnect and reconnect.
    Optionally returns read data as lines
    and has hooks for authorization.
    """
    # states
    Connecting = 5
    Authorizing = 4
    Connected = 3
    Disconnecting = 2
    Failing = 1
    Disconnected = 0
    Failed = -1

    # a dictionary that describes the various values for the connection state
    _StateDict = {
        Connecting: "Connecting",
        Authorizing: "Authorizing",
        Connected: "Connected",
        Disconnecting: "Disconnecting",
        Failing: "Failing",
        Disconnected: "Disconnected",
        Failed: "Failed",
    }
    def __init__(self,
        host = None,
        port = 23,
        readCallback = None,
        readLines = False,
        stateCallback = None,
        authReadCallback = None,
        authReadLines = False,
        name = "",
    ):
        """Construct a TCPConnection

        Inputs:
        - host: initial host (can be changed when connecting)
        - port: initial port (can be changed when connecting);
          defaults to 23, the standard telnet port
        - readCallback: function to call whenever data is read;
          see addReadCallback for details.
        - readLines: if True, the read callbacks receive entire lines
            minus the terminator; otherwise the data is distributed as received
        - stateCallback: a function to call whenever the state or reason changes;
          see addStateCallback for details.
        - authReadCallback: if specified, used as the initial read callback function;
            if auth succeeds, it must call self._authDone()
        - authReadLines: if True, the auth read callback receives entire lines
        - name: a string to identify this object; strictly optional
        """        
        self.host = host
        self.port = port
        self._readLines = bool(readLines)
        self._userReadCallbacks = []
        if readCallback:
            self.addReadCallback(readCallback)
        self._stateCallbacks = []
        if stateCallback:
            self.addStateCallback(stateCallback)
        self._authReadLines = bool(authReadLines)
        self._authReadCallback = authReadCallback
        self._name = name

        self._state = 0
        self._reason = ""
        self._currReadCallbacks = []
        
        # translation table from TCPSocket states to local states
        # note that the translation of Connected will depend
        # on whether there is authorization; this initial setup
        # assumes no authorization
        if self._authReadCallback:
            locConnected = self.Authorizing
        else:
            locConnected = self.Connected
        self._localSocketStateDict = {
            TCPSocket.Connecting: self.Connecting,
            TCPSocket.Connected: locConnected,
            TCPSocket.Closing: self.Disconnecting,
            TCPSocket.Failing: self.Failing,
            TCPSocket.Closed: self.Disconnected,
            TCPSocket.Failed: self.Failed,
        }
        
        self._sock = NullSocket()
        
    def addReadCallback(self, readCallback):
        """Add a read function, to be called whenever data is read.
        
        Inputs:
        - readCallback: function to call whenever a line of data is read;
          it is sent two arguments:
          - the socket (a TCPSocket object)
          - the data read; in line mode the line terminator is stripped
        """
        assert callable(readCallback), "read callback not callable"
        self._userReadCallbacks.append(readCallback)
    
    def addStateCallback(self, stateCallback, callNow=False):
        """Add a state function to call whenever the state or reason changes.
        
        Inputs:
        - stateCallback: the function; it is sent one argument: this TCPConnection
        - callNow: call the connection function immediately?
        """
        assert callable(stateCallback)
        self._stateCallbacks.append(stateCallback)
        if callNow:
            stateCallback(self)

    def connect(self,
        host=None,
        port=None,
    ):
        """Open the connection.

        Inputs:
        - host: IP address (name or numeric) of host; if omitted, the default is used
        - port: port number; if omitted, the default is used
        
        Raise RuntimeError if:
        - already connecting or connected
        - host omitted and self.host not already set
        """
        if not self.mayConnect():
            raise RuntimeError("Cannot connect: already connecting or connected")
        if not (host or self.host):
            raise RuntimeError("Cannot connect: no host specified")

        self.host = host or self.host
        self.port = port or self.port
        
        self._sock.setStateCallback() # remove socket state callback
        if not self._sock.isClosed():
            self._sock.close()

        self._sock = TCPSocket(
            addr = self.host,
            port = self.port,
            stateCallback = self._sockStateCallback,
            name = self._name,
        )
        
        if self._authReadCallback:
            self._localSocketStateDict[TCPSocket.Connected] = self.Authorizing
            self._setRead(True)
        else:
            self._localSocketStateDict[TCPSocket.Connected] = self.Connected
            self._setRead(False)
    
    def disconnect(self, isOK=True, reason=None):
        """Close the connection.

        Called disconnect instead of close (the usual counterpoint in the socket library)
        because you can reconnect at any time by calling connect.
        
        Inputs:
        - isOK: if True, final state is Disconnected, else Failed
        - reason: a string explaining why, or None to leave unchanged;
            please specify a reason if isOK is false!   
        """
        self._sock.close(isOK=isOK, reason=reason)

    def getFullState(self):
        """Returns the current state as a tuple:
        - state: a numeric value; named constants are available
        - stateStr: a short string describing the state
        - reason: the reason for the state ("" if none)
        """
        state, reason = self._state, self._reason
        try:
            stateStr = self._StateDict[state]
        except KeyError:
            stateStr = "Unknown (%r)" % (state)
        return (state, stateStr, reason)

    def getState(self):
        """Returns the current state as a constant.
        """
        return self._state
    
    def isConnected(self):
        """Return True if connected, False otherwise.
        """
        return self._state == self.Connected

    def isDone(self):
        """Return True if connected, disconnected or failed.
        """
        return self._state in (self.Connected, self.Disconnected, self.Failed)
    
    def mayConnect(self):
        """Return True if one may call connect, false otherwise"""
        return self._state not in (self.Connected, self.Connecting, self.Authorizing)

    def removeReadCallback(self, readCallback):
        """Attempt to remove the read callback function;

        Returns True if successful, False if the subr was not found in the list.
        """
        try:
            self._userReadCallbacks.remove(readCallback)
            return True
        except ValueError:
            return False

    def removeStateCallback(self, stateCallback):
        """Attempt to remove the state callback function;

        Returns True if successful, False if the subr was not found in the list.
        """
        try:
            self._stateCallbacks.remove(stateCallback)
            return True
        except ValueError:
            return False
    
    def write(self, astr):
        """Write data to the socket. Does not block.
        
        Safe to call as soon as you call connect, but of course
        no data is sent until the connection is made.
        
        Raises UnicodeError if the data cannot be expressed as ascii.
        Raises RuntimeError if the socket is not connecting or connected.
        If an error occurs while sending the data, the socket is closed,
        the state is set to Failed and _reason is set.
        """
        self._sock.write(astr)

    def writeLine(self, astr):
        """Send a line of data, appending newline.

        Raises UnicodeError if the data cannot be expressed as ascii.
        Raises RuntimeError if the socket is not connecting or connected.
        If an error occurs while sending the data, the socket is closed,
        the state is set to Failed and _reason is set.
        """
        self._sock.writeLine(astr)
    
    def _authDone(self, msg=""):
        """Call from your authorization callback function
        when authorization succeeds.
        Do not call unless you specified an authorization callback function.
        
        If authorization fails, call self.disconnect(False, error msg) instead.
        """
        self._setRead(forAuth=False)
        self._setState(self.Connected, msg)
    
    def _setRead(self, forAuth=False):
        """Set up reads.
        """
        if (forAuth and self._authReadLines) or (not forAuth and self._readLines):
            self._sock.setReadCallback(self._sockReadLineCallback)
        else:
            self._sock.setReadCallback(self._sockReadCallback)
        if forAuth:
            self._currReadCallbacks = [self._authReadCallback,]
        else:
            self._currReadCallbacks = self._userReadCallbacks

    def _setState(self, newState, reason=None):
        """Set the state and reason. If anything has changed, call the connection function.

        Inputs:
        - newState  one of the state constants defined at top of file
        - reason    the reason for the change (a string, or None to leave unchanged)
        """
        #print "_setState(newState=%s, reason=%s); self._stateCallbacks=%s" % (newState, reason, self._stateCallbacks)
        oldStateReason = (self._state, self._reason)
        if not self._StateDict.has_key(newState):
            raise RuntimeError, "unknown connection state: %s" % (newState,)
        self._state = newState
        if reason != None:
            self._reason = str(reason)
        
        # if the state or reason has changed, call state callbacks
        if oldStateReason != (self._state, self._reason):
            for stateCallback in self._stateCallbacks:
                stateCallback(self)
    
    def _sockReadCallback(self, sock):
        """Read callback for the socket in binary mode (not line mode).
                
        When data is received, read it and issues all callbacks.
        """
        dataRead = sock.read()
        #print "%s._sockReadCallback(sock=%r) called; data=%r" % (self, sock, dataRead)
        for subr in self._currReadCallbacks:
            subr(sock, dataRead)

    def _sockReadLineCallback(self, sock):
        """Read callback for the socket in line mode.
                
        Whenever a line is received, issues all callbacks, first stripping the line terminator.
        """
        dataRead = sock.readLine()
        if dataRead is None:
            # only a partial line was available
            return
        #print "%s._sockReadLineCallback(sock=%r) called with data %r" % (self, sock, dataRead)
        for subr in self._currReadCallbacks:
            subr(sock, dataRead)
    
    def _sockStateCallback(self, sock):
        sockState, descr, reason = sock.getFullState()
        try:
            locState = self._localSocketStateDict[sockState]
        except KeyError:
            sys.stderr.write("unknown TCPSocket state %r\n" % sockState)
            return
        self._setState(locState, reason)

    def _getArgStr(self):
        """Return main arguments as a string, for __str__
        """
        return "name=%r" % (self._name)

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self._getArgStr())
        

if __name__ == "__main__":
    import Tkinter
    
    root = Tkinter.Tk()
    
    def statePrt(sock):
        stateVal, stateStr, reason = sock.getFullState()
        if reason:
            print "socket %s: %s" % (stateStr, reason)
        else:
            print "socket %s" % (stateStr,)
        
    def readPrt(sock, outStr):
        print "read: %r" % (outStr,)

    ts = TCPConnection(
        readLines = True,
        host = "localhost",
        port = 7,
        stateCallback = statePrt,
        readCallback = readPrt,
    )
    ts.connect()
    
    root.mainloop()
