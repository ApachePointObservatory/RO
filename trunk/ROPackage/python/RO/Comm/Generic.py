#!/usr/bin/env python
"""Generic classes for event-based communication and timing.
Generic in the sense that it supports both Twisted framework and Tcl sockets.

Includes:
- TCPSocket: a socket for TCP/IP communications
- TCPServer: a socket server for TCP/IP communications
- Timer: a one-shot timer

WARNING: before using any of these objects you must do two things:
- Set up the event loop
- Call setFramework to choose your framework

Here are some examples:

1) Using Tkinter with the Tcl event loop (no Twisted)

import Tkinter
root = Tkinter.Tk()

import RO.Comm.Generic
RO.Comm.Generic.setFramework("tk")
#...
#...code that uses RO.Comm.Generic here
#...
root.mainloop()

2) Using Twisted framework

# if you want Twisted to use something other than the select reactor, set it up here
# ...
from twisted.internet import reactor

import RO.Comm.Generic
RO.Comm.Generic.setFramework("twisted")
# ...
# ...code that uses RO.Comm.Generic here
#...
reactor.run()

3) Using Twisted framework with Tkinter

import Tkinter
import twisted.internet.tksupport
root = Tkinter.Tk()
twisted.internet.tksupport.install(root)
from twisted.internet import reactor

import RO.Comm.Generic
RO.Comm.Generic.setFramework("twisted")
# ...
# ...code that uses RO.Comm.Generic here
#...
reactor.run()

History:
2012-08-10 ROwen
"""
import time
from RO.AddCallback import safeCall

_Framework = None

def setFramework(framework):
    """Set which framework you wish to use.
    
    WARNING: you must set up your event loop and call setFramework
    before using any of the objects in this module.
    See the module doc string for more information and examples.

    Inputs
    - framework: one of "tk" or "twisted". See the module doc string for more information.
    """
    global _Framework, TCPSocket, TCPServer, Timer
    if framework not in getFrameworkSet():
        frameworkList = sorted(list(getFrameworkSet()))
        raise ValueError("framework=%r; must be one of %s" % (frameworkList,))

    if framework == "tk":
        from RO.Comm.TkSocket import TCPSocket, TCPServer
        from RO.TkUtil import Timer
    elif framework == "twisted":
        from RO.Comm.TwistedSocket import TCPSocket, TCPServer
        from RO.Comm.TwistedTimer import Timer
    else:
        raise ValueError("Bug! Unrecognized framework=%r" % (framework,))
    _Framework = framework

def getFramework():
    """Return selected framework, or None if none has been selected
    """
    return _Framework

def getFrameworkSet():
    """Return the set of supported frameworks
    """
    return set(("tk", "twisted"))


class WaitForTCPServer(object):
    """Wait for a TCP server to accept a connection
    """
    def __init__(self, host, port, callFunc, timeLim=5, pollInterval=0.2):
        """Start waiting for a TCP server to accept a connection
        
        @param[in] host: host address of server
        @param[in] port: port number of server
        @param[in] callFunc: function to call when server ready or wait times out;
            receives one parameter: this object
        @param[in] timeLim: approximate maximum wait time (sec);
            the actual wait time may be up to pollInterval longer
        @param[in] pollInterval: interval at which to poll (sec)
        
        Useful attributes:
        - isDone: the wait is over
        - didFail: the wait failed
        """
        self.host = host
        self.port = port
        self.isDone = False
        self.didFail = False
        self._callFunc = callFunc
        self._pollInterval = float(pollInterval)
        self._timeLim = float(timeLim)
        self._pollTimer = Timer()
        self._startTime = time.time()
        self._tryConnection()
        self._timeoutTimer = Timer(timeLim, self._finish)
    
    def _tryConnection(self):
        """Attempt a connection
        """
        self._sock = TCPSocket(host=self.host, port=self.port, stateCallback=self._sockStateCallback)
    
    def _sockStateCallback(self, sock):
        """Socket state callback
        """
        if sock.isReady:
            # success
            self._finish()
        elif sock.isDone:
            # connection failed; try again
            self._pollTimer.start(self._pollInterval, self._tryConnection)
        
    def _finish(self):
        """Set _isReady and call the callback function
        """
        self._pollTimer.cancel()
        self._timeoutTimer.cancel()
        self.didFail = not self._sock.isReady
        self.isDone = True
        if not self._sock.isDone:
            self._sock.setStateCallback()
            self._sock.close()
            self._sock = None
        if self._callFunc:
            callFunc = self._callFunc
            self._callFunc = None
            safeCall(callFunc, self)

if __name__ == "__main__":
    import Tkinter
    root = Tkinter.Tk()
    root.withdraw()
    setFramework("tk") # since it is almost always installed
    
    port = 2150
            
    testStrings = (
        "string with 3 nulls: 1 \0 2 \0 3 \0 end",
        "string with 3 quoted nulls: 1 \\0 2 \\0 3 \\0 end",
        '"quoted string followed by carriage return"\r',
        "string with newline: \n end",
        "string with carriage return: \r end",
        "quit",
    )
    
    strIter = iter(testStrings)

    def runTest():
        try:
            testStr = strIter.next()
            print "Client writing %r" % (testStr,)
            clientSocket.writeLine(testStr)
            Timer(0.5, runTest)
        except StopIteration:
            pass

    def clientRead(sock):
        outStr = sock.readLine(default="")
        print "Client read   %r" % (outStr,)
        if outStr == "quit":
            print "*** Data exhausted; closing the client connection"
            clientSocket.close()

    def clientState(sock):
        state, reason = sock.fullState
        if reason:
            print "Client %s: %s" % (state, reason)
        else:
            print "Client %s" % (state,)
        if sock.isDone:
            print "*** Client closed; now halting Tk event loop (which kills the server)"
            root.quit()
        if sock.isReady:
            print "*** Client connected; now sending test data"
            runTest()

    def serverState(server):
        state, reason = server.fullState
        if reason:
            print "Server %s: %s" % (state, reason)
        else:
            print "Server %s" % (state,)
        if server.isReady:
            print "*** Echo server ready; now starting up a client"
            startClient()
    
    def startClient():
        global clientSocket
        clientSocket = TCPSocket(
            host = "localhost",
            port = port,
            stateCallback = clientState,
            readCallback = clientRead,
            name = "client",
        )
    
    class EchoServer(TCPServer):
        def __init__(self, port, stateCallback):
            TCPServer.__init__(self,
                port = port,
                stateCallback = stateCallback,
                sockReadCallback = self.sockReadCallback,
                name = "echo",
            )

        def sockReadCallback(self, sock):
            readLine = sock.readLine(default="")
            sock.writeLine(readLine)

    print "*** Starting echo server on port", port
    echoServer = EchoServer(port = port, stateCallback = serverState)
    
    root.mainloop()
