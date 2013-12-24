#!/usr/bin/env python
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
2012-08-01 ROwen    Added support for Twisted framework.
                    You must now call RO.Comm.Generic.setFramework before importing this module.
                    Many methods are now properties, e.g. isDone->isDone.
                    Added name attribute to TCPConnection.
2012-11-29 ROwen    Overhauled demo code.
2012-12-06 ROwen    Set tk as RO.Comm.Generic framework if not already set.
2012-12-17 ROwen    Initial state was 0, should have been Disconnected.
"""
import sys
from RO.Comm.BaseSocket import NullSocket
import RO.Comm.Generic
if RO.Comm.Generic.getFramework() is None:
    print "Warning: RO.Comm.Generic framework not set; setting to tk"
    RO.Comm.Generic.setFramework("tk")
from RO.Comm.Generic import TCPSocket

class TCPConnection(object):
    """A TCP Socket with the ability to disconnect and reconnect.
    Optionally returns read data as lines
    and has hooks for authorization.
    """
    # states
    Connecting = "Connecting"
    Authorizing = "Authorizing"
    Connected = "Connected"
    Disconnecting = "Disconnecting"
    Failing = "Failing"
    Disconnected = "Disconnected"
    Failed = "Failed"

    _AllStates = set((
        Connecting,
        Authorizing,
        Connected,
        Disconnecting,
        Failing,
        Disconnected,
        Failed,
    ))
    _ConnectedStates = set((Connected,))
    _DoneStates = set((Connected, Disconnected, Failed))
    _FailedStates = set((Failed,))
    
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

        self._state = self.Disconnected
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
        timeLim=None,
    ):
        """Open the connection.

        Inputs:
        - host: IP address (name or numeric) of host; if omitted, the default is used
        - port: port number; if omitted, the default is used
        - timeLim: time limit (sec); if None then no time limit
        
        If using twisted framework then returns Socket.readyDeferred, which is either
        a Deferred or None if there is nothing to defer. Otherwise returns None.
        
        Raise RuntimeError if:
        - already connecting or connected
        - host omitted and self.host not already set
        """
        if not self.mayConnect:
            raise RuntimeError("Cannot connect: already connecting or connected")
        if not (host or self.host):
            raise RuntimeError("Cannot connect: no host specified")

        self.host = host or self.host
        self.port = port or self.port
        
        self._sock.setStateCallback() # remove socket state callback
        if not self._sock.isDone:
            self._sock.close()

        self._sock = TCPSocket(
            host = self.host,
            port = self.port,
            stateCallback = self._sockStateCallback,
            timeLim = timeLim,
            name = self._name,
        )
        
        if self._authReadCallback:
            self._localSocketStateDict[TCPSocket.Connected] = self.Authorizing
            self._setRead(True)
        else:
            self._localSocketStateDict[TCPSocket.Connected] = self.Connected
            self._setRead(False)
        
        if hasattr(self._sock, "getReadyDeferred"):
            return self._sock.getReadyDeferred()
        return None
    
    def disconnect(self, isOK=True, reason=None):
        """Close the connection.

        Called disconnect instead of close (the usual counterpoint in the socket library)
        because you can reconnect at any time by calling connect.

        If using twisted framework then returns a Deferred, or None if there is nothing to defer.
        
        Inputs:
        - isOK: if True, final state is Disconnected, else Failed
        - reason: a string explaining why, or None to leave unchanged;
            please specify a reason if isOK is false!   
        """
        print "close the socket"
        a = self._sock.close(isOK=isOK, reason=reason)
        print "close returned a=", a
        return a

    @property
    def fullState(self):
        """Returns the current state as a tuple:
        - state: the state, as a string
        - reason: the reason for the state ("" if none)
        """
        return (self._state, self._reason)

    @property
    def state(self):
        """Returns the current state as a string.
        """
        return self._state
    
    @property
    def isConnected(self):
        """Return True if connected, False otherwise.
        """
        return self._state in self._ConnectedStates

    @property
    def isDone(self):
        """Return True if the last transition is finished, i.e. connected, disconnected or failed.
        """
        return self._state in self._DoneStates
    
    @property
    def didFail(self):
        """Return True if the connection failed
        """
        return self._state in self._FailedStates
    
    @property
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
        if newState not in self._AllStates:
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
        sockState, reason = sock.fullState
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
    """Demo using a simple echo server.
    """
    import Tkinter
    root = Tkinter.Tk()
    root.withdraw()
    from RO.Comm.Generic import TCPServer
    from RO.TkUtil import Timer
    
    clientConn = None
    echoServer = None
    didConnect = False
    
    port = 2150
            
    testStrings = (
        "string with 3 nulls: 1 \0 2 \0 3 \0 end",
        "string with 3 quoted nulls: 1 \\0 2 \\0 3 \\0 end",
        '"quoted string followed by carriage return"\r',
        '',
        u"unicode string",
        "string with newline: \n end",
        "string with carriage return: \r end",
        "quit",
    )
    
    strIter = iter(testStrings)

    def runTest():
        global clientConn
        try:
            testStr = strIter.next()
            print "Client writing %r" % (testStr,)
            clientConn.writeLine(testStr)
            Timer(0.001, runTest)
        except StopIteration:
            pass

    def clientRead(sock, outStr):
        global clientConn
        print "Client read    %r" % (outStr,)
        if outStr and outStr.strip() == "quit":
            print "*** Data exhausted; disconnecting client connection"
            clientConn.disconnect()
            

    def clientState(conn):
        global didConnect, echoServer
        state, reason = conn.fullState
        if reason:
            print "Client %s: %s" % (state, reason)
        else:
            print "Client %s" % (state,)
        if conn.isConnected:
            print "*** Client connected; now sending test data"
            didConnect = True
            runTest()
        elif didConnect is conn.isDone:
            print "*** Client disconnected; closing echo server ***"
            echoServer.close()

    def serverState(server):
        state, reason = server.fullState
        if reason:
            print "Server %s: %s" % (state, reason)
        else:
            print "Server %s" % (state,)
        if server.isReady:
            print "*** Echo server ready; now starting up a client"
            startClient()
        elif server.isDone:
            print "*** Halting the tcl event loop"
            root.quit()

    def startClient():
        global clientConn
        clientConn = TCPConnection(
            host = "localhost",
            port = port,
            stateCallback = clientState,
            readCallback = clientRead,
            name = "client",
        )
        clientConn.connect()
    
    class EchoServer(TCPServer):
        def __init__(self, port, stateCallback):
            TCPServer.__init__(self,
                port = port,
                stateCallback = stateCallback,
                sockReadCallback = self.sockReadCallback,
                name = "echo",
            )

        def sockReadCallback(self, sock):
            readLine = sock.readLine(default=None)
            if readLine is not None:
                sock.writeLine(readLine)

    print "*** Starting echo server on port %s" % (port,)
    echoServer = EchoServer(port = port, stateCallback = serverState)
    
    root.mainloop()
