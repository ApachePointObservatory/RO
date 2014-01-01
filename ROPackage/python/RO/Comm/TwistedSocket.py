#!/usr/bin/env python
"""BasicSocket wrapper that works with the Twisted framework

The intention is to work with TCPConnection and all the infrastructure that uses it.

History:
2012-07-19 ROwen
2012-11-29 ROwen    Misfeature fix: write and writeLine failed on unicode strings that could be converted to ASCII
                    (a "feature" of Twisted Framework).
2013-12-24 ROwen    Added timeLim argument to socket constructors.
                    TCPSocket.port now returns the auto-selected port if constructed with port=0.
                    Added experimental support for Deferreds; it's messy so I plan to remove it again.
2014-01-01 ROwen    Removed experimental support for Deferreds.
"""
__all__ = ["Socket", "TCPSocket", "Server", "TCPServer"]

import re
import sys
import traceback
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint
from twisted.internet import reactor
from twisted.python import log
from RO.Comm.BaseSocket import BaseSocket, BaseServer, nullCallback
from RO.Comm.TwistedTimer import Timer

class _SocketProtocol(Protocol):
    """Twisted socket protocol for use with these socket classes

    Based on twisted LineReceiver protocol.
    
    lineEndPattern: line-ending delimiters used by readLine, as a compiled regular expression.
        By default it uses any of \r\n, \r or \n
    """
    lineEndPattern = re.compile("\r\n|\r|\n")
    
    def __init__(self):
        self._readCallback = nullCallback
        self._connectionLostCallback = nullCallback
        self.__buffer = ""
    
    def roSetCallbacks(self, readCallback, connectionLostCallback):
        """Add Socket-specific callbacks
        
        Inputs:
        - readCallback: a function that receives one argument: the read data
        - connectionLostCallback: a function that receives one argument: a Twisted error object
        """
        self._readCallback = readCallback
        self._connectionLostCallback = connectionLostCallback

    def clearLineBuffer(self):
        """
        Clear buffered data.

        @return: All of the cleared buffered data.
        @rtype: C{str}
        """
        b = self.__buffer
        self.__buffer = ""
        return b
    
    def read(self, nChar):
        """Read at most nChar characters; if nChar=None then get all chars
        """
        if nChar is None:
            data, self.__buffer = self.__buffer, ""
        else:
            data, self._buffer = self._buffer[0:nChar], self._buffer[nChar:]
        #print "%s.read(nChar=%r) returning %r; remaining buffer=%r" % (self, nChar, data, self.__buffer)

        if self.__buffer and self._readCallback:
            Timer(0.000001, self._readCallback, self)
        return data
        
    def readLine(self, default=None):
        """Read a line of data; return default if a line is not present
        """
        res = self.lineEndPattern.split(self.__buffer, 1)
        if len(res) == 1:
            # readDelimiter not found; leave the buffer alone and don't bother to call the callback again
            #print "%s.readLine(default=%r) returning the default; remaining buffer=%r" % (self, default, self.__buffer)
            return default
        self.__buffer = res[1]
        #print "%s.readLine(default=%r) returning %r; remaining buffer=%r" % (self, default, res[0], self.__buffer)

        if self.__buffer and self._readCallback:
            Timer(0.000001, self._readCallback, self)
        return res[0]
        
    def dataReceived(self, data):
        """
        Protocol.dataReceived.
        Translates bytes into lines, and calls lineReceived (or
        rawDataReceived, depending on mode.)
        """
        self.__buffer = self.__buffer + data
        self._readCallback(self)
    
    def connectionMade(self):
        """The connection was successfully made
        """
        #print "%s.connectionMade(); self.factory._connectionMadeCallback=%s" % (self, self.factory._connectionMadeCallback)
        self.factory._connectionMadeCallback(self)
    
    def connectionLost(self, reason):
        """The connection was lost (whether by request or error)
        """
        #print "%s.connectionLost(reason=%s)" % (self, reason)
        self._connectionLostCallback(reason)
    
    def roAbort(self):
        """Discard callbacks and abort the connection
        """
        #print "%s.roAbort()" % (self,)
        self._readCallback = nullCallback
        self._connectionLostCallback = nullCallback
        if self.transport:
            self.transport.abortConnection()
    
    def __str__(self):
        return "%s" % (self.__class__.__name__,)

    
class _SocketProtocolFactory(Factory):
    """Twisted _SocketProtocol factory for use with these socket classes
    """
    protocol = _SocketProtocol
    
    def __init__(self, connectionMadeCallback = nullCallback):
        self._connectionMadeCallback = connectionMadeCallback


class Socket(BaseSocket):
    """A socket using Twisted framework.
    """
    def __init__(self,
        endpoint = None,
        protocol = None,
        state = BaseSocket.Connected,
        readCallback = nullCallback,
        stateCallback = nullCallback,
        timeLim = None,
        name = "",
    ):
        """Construct a Socket

        Inputs:
        - endpoint  a Twisted endpoint, e.g. twisted.internet.endpoints.TCP4ClientEndpoint;
        - protocol  a Twisted protocol;
            you must either specify endpoint or protocol, but not both
        - state     the initial state
        - readCallback  function to call when data read; receives: self
        - stateCallback a state callback function; see addStateCallback for details
        - timeLim   time limit to make connection (sec); no limit if None or 0
        - name      a string to identify this socket; strictly optional
        """
        #print "Socket(name=%r, endpoint=%r, protocol=%r, state=%r, readCallback=%r, stateCallback=%r)" % \
        #    (name, endpoint, protocol, state, readCallback, stateCallback)
        if bool(endpoint is None) == bool(protocol is None):
            raise RuntimeError("Must provide one of endpoint or protocol")
        self._endpoint = endpoint
        self._endpointDeferred = None
        self._protocol = None
        self._data = None
        self._connectTimer = Timer()
        BaseSocket.__init__(self,
            state = state,
            readCallback = readCallback,
            stateCallback = stateCallback,
            name = name
        )
        if protocol is not None:
            self._connectionMade(protocol)
        else:
            if timeLim:
                self._connectTimer.start(timeLim, self._connectTimeout)
            self._setState(BaseSocket.Connecting)
            self._endpointDeferred = self._endpoint.connect(_SocketProtocolFactory())
            setCallbacks(self._endpointDeferred, self._connectionMade, self._connectionLost)
    
    @property
    def host(self):
        """Return the address, or None if not known
        """
        if self._protocol:
            return getattr(self._protocol.transport.getPeer(), "host", None)
        return None

    @property
    def port(self):
        """Return the port, or None if unknown
        """
        if self._protocol:
            return getattr(self._protocol.transport.getPeer(), "port", None)
        return None

    def _clearCallbacks(self):
        """Clear any callbacks added by this class. Called just after the socket is closed.
        """
        BaseSocket._clearCallbacks(self)
        self._connCallback = None
        if self._endpointDeferred is not None:
            self._endpointDeferred.cancel()
            self._endpointDeferred = None
        if self._protocol is not None:
            self._protocol.roAbort()
            self._protocol = None

    def _connectionLost(self, reason):
        """Connection lost callback
        """
        #print "%s._connectionLost(reason=%r)" % (self, reason)
        if reason is None:
            reasonStrOrNone = None
        elif isinstance(reason, ConnectionDone):
            # connection closed cleanly; no need for a reason
            # use getattr in case reason as no type attribute
            reasonStrOrNone = None
        else:
            reasonStrOrNone = str(reason)

        if self._state == BaseSocket.Closing:
            self._setState(BaseSocket.Closed, reasonStrOrNone)
        else:
            self._setState(BaseSocket.Failed, reasonStrOrNone)
    
    def _connectionMade(self, protocol):
        """Callback when connection made
        """
        #print "%s._connectionMade(protocol=%r)" % (self, protocol)
        self._protocol = protocol
        self._protocol.roSetCallbacks(
            readCallback = self._doRead,
            connectionLostCallback = self._connectionLost,
        )
        self._setState(BaseSocket.Connected)

    def _basicClose(self):
        """Close the socket.
        """
        if self._protocol is not None:
            self._protocol.transport.loseConnection()
    
    def read(self, nChar=None):
        """Read data. Do not block.
        
        Inputs:
        - nChar: maximum number of chars to return; if None then all available data is returned.
        
        Raise RuntimeError if the socket is not connected.
        """
        if not self.isReady:
            raise RuntimeError("%s not connected" % (self,))
        return self._protocol.read(nChar)
    
    def readLine(self, default=None):
        """Read one line of data, not including the end-of-line indicator. Do not block.
        
        Any of \r\n, \r or \n are treated as end of line.
        
        Inputs:
        - default   value to return if a full line is not available
                    (in which case no data is read)
        
        Raise RuntimeError if the socket is not connected.
        """
        if not self.isReady:
            raise RuntimeError("%s not connected" % (self,))
        return self._protocol.readLine(default)
    
    def write(self, data):
        """Write data to the socket (without blocking)
        
        Safe to call as soon as you call connect, but of course
        no data is sent until the connection is made.
        
        Raise UnicodeError if the data cannot be expressed as ascii.
        Raise RuntimeError if the socket is not connecting or connected.
        If an error occurs while sending the data, the socket is closed,
        the state is set to Failed and _reason is set.
        
        An alternate technique (from Craig):
        turn } into \}; consider escaping null and all but
        the final \n in the same fashion
        (to do this it probably makes sense to supply a writeLine
        that escapes \n and \r and then appends \n).
        Then:
        self._tk.eval('puts -nonewline %s { %s }' % (self._sock, escData))
        """
        #print "%s.write(%r)" % (self, data)
        if not self.isReady:
            raise RuntimeError("%s not connected" % (self,))
        self._protocol.transport.write(str(data))
    
    def writeLine(self, data):
        """Write a line of data terminated by standard newline
        """
        #print "%s.writeLine(data=%r)" % (self, data)
        if not self.isReady:
            raise RuntimeError("%s not connected" % (self,))
        self.write(data + "\r\n")
    
    def _connectTimeout(self):
        """Call if connection times out
        """
        if not self.isReady or self.isDone:
            self.close(isOK=False, reason="timeout")
    
    def _doRead(self, sock):
        """Called when there is data to read
        """
        if self._readCallback:
            try:
                self._readCallback(self)
            except Exception, e:
                sys.stderr.write("%s read callback %s failed: %s\n" % (self, self._readCallback, e,))
                traceback.print_exc(file=sys.stderr)

    def _setState(self, *args, **kwargs):
        BaseSocket._setState(self, *args, **kwargs)
        if self.isReady or self.isDone:
            self._connectTimer.cancel()


class TCPSocket(Socket):
    """A TCP/IP socket using Twisted framework.
    """
    def __init__(self,
        host = None,
        port = None,
        readCallback = None,
        stateCallback = None,
        timeLim = None,
        name = "",
    ):
        """Construct a TCPSocket
    
        Inputs:
        - host      the IP address
        - port      the port
        - readCallback  function to call when data read; receives: self
        - stateCallback a state callback function; see addStateCallback for details
        - timeLim   time limit to make connection (sec); no limit if None or 0
        - name      a string to identify this socket; strictly optional
        """
        endpoint = TCP4ClientEndpoint(reactor, host=host, port=port)
        Socket.__init__(self,
            endpoint = endpoint,
            readCallback = readCallback,
            stateCallback = stateCallback,
            timeLim = timeLim,
            name = name,
        )

    def _getArgStr(self):
        return "name=%r, host=%r, port=%r" % (self.name, self.host, self.port)


class Server(BaseServer):
    """A socket server using Twisted framework.
    """
    def __init__(self,
        endpoint,
        connCallback = None,
        stateCallback = None,
        sockReadCallback = None,
        sockStateCallback = None,
        name = "",
    ):
        """Construct a socket server
        
        Inputs:
        - endpoint: a Twisted endpoint, e.g. twisted.internet.endpoints.TCP4ClientEndpoint
        - connCallback: function to call when a client connects; it receives the following arguments:
                    - sock, a Socket
        - stateCallback: function to call when server changes state; it receives one argument: this server
        - sockReadCallback: function for each server socket to call when it receives data;
            See BaseSocket.addReadCallback for details
        - sockStateCallback: function for each server socket to call when it receives data
            See BaseSocket.addStateCallback for details
        - name: a string to identify this socket; strictly optional
        """
        self._endpoint = endpoint
        self._protocol = None
        self._closeDeferred = None
        BaseServer.__init__(self,
            connCallback = connCallback,
            stateCallback = stateCallback,
            sockReadCallback = sockReadCallback,
            sockStateCallback = sockStateCallback,
            name = name,
        )
        self._numConn = 0
        Timer(0, self._startListening) # let device be fully constructed before listening
            # I'm not sure why this is needed, but it seems to help
    
    def _startListening(self):
        """Start listening for new connections
        """
        self._endpointDeferred = self._endpoint.listen(_SocketProtocolFactory(self._newConnection))
        setCallbacks(self._endpointDeferred, self._listeningCallback, self._connectionLost)

    @property
    def port(self):
        """Return the port, or None if not known
        """
        port = getattr(self._protocol, "port", None)
        if port == 0: # try an undocumented interface
            port = getattr(self._protocol, "_realPortNumber", None)
        return port

    def _listeningCallback(self, protocol):
        self._protocol = protocol
        self._setState(self.Listening)

    def _basicClose(self):
        """Shut down the server.
        """
        if self._protocol is not None:
            self._closeDeferred = self._protocol.stopListening()
            setCallbacks(self._closeDeferred, self._connectionLost, self._connectionLost)
    
    def _clearCallbacks(self):
        """Clear any callbacks added by this class. Called just after the socket is closed.
        """
        BaseServer._clearCallbacks(self)
        self._connCallback = nullCallback
        if self._endpointDeferred:
            self._endpointDeferred.cancel()
            self._endpointDeferred = None
        if self._closeDeferred:
            self._closeDeferred.cancel()
            self._closeDeferred = None
    
    def _connectionLost(self, reason):
        """Connection failed callback
        """
        #print "%s._connectionLost(%s)" % (self, reason)
        if reason is None:
            reasonStrOrNone = None
        elif issubclass(getattr(reason, "type", None), ConnectionDone):
            # connection closed cleanly; no need for a reason
            # use getattr in case reason as no type attribute
            reasonStrOrNone = None
        else:
            reasonStrOrNone = str(reason)

        if self._state == BaseSocket.Closing:
            self._setState(BaseSocket.Closed, reasonStrOrNone)
        else:
            self._setState(BaseSocket.Failed, reasonStrOrNone)
    
    def _newConnection(self, protocol):
        """A client has connected. Create a Socket and call the connection callback with it.
        """
        #print "Server._newConnection(%r)" % (protocol,)
        self._numConn += 1
        newSocket = Socket(
            protocol = protocol,
            readCallback = self._sockReadCallback,
            stateCallback = self._sockStateCallback,
            name = "%s%d" % (self.name, self._numConn,)
        )

        try:
            self._connCallback(newSocket)
        except Exception, e:
            errMsg = "%s connection callback %s failed: %s" % (self.__class__.__name__, self._connCallback, e)
            sys.stderr.write(errMsg + "\n")
            traceback.print_exc(file=sys.stderr)


class TCPServer(Server):
    """A TCP/IP socket server using Twisted framework.
    """
    def __init__(self,
        port,
        connCallback = None,
        stateCallback = None,
        sockReadCallback = None,
        sockStateCallback = None,
        name = "",
    ):
        """Construct a socket server
        
        Inputs:
        - port: the port on which to listen for new connections
        - connCallback: function to call when a client connects; it receives the following arguments:
                    - sock, a Socket
        - stateCallback: function to call when server changes state; it receives one argument: this server
        - sockReadCallback: function for each server socket to call when it receives data;
            See BaseSocket.addReadCallback for details
        - sockStateCallback: function for each server socket to call when it receives data
            See BaseSocket.addStateCallback for details
        - name: a string to identify this socket; strictly optional
        """
        endpoint = TCP4ServerEndpoint(reactor, port=port)
        Server.__init__(self,
            endpoint = endpoint,
            connCallback = connCallback,
            stateCallback = stateCallback,
            sockReadCallback = sockReadCallback,
            sockStateCallback = sockStateCallback,
            name = name,
        )

    def _getArgStr(self):
        """Return main arguments as a string, for __str__
        """
        return "name=%r, port=%r" % (self.name, self.port)

def setCallbacks(deferred, callback, errback):
    """Convenience function to add callbacks to a deferred
    
    Also adds a final logging errback.
    
    This exists due to an obscure error in the pattern I was using:
        self.deferred = ... (create the deferred somehow)
        self.deferred.addCallbacks(callfunc, errfunc)
        # the previous statement may fire errfunc immediately,
        # which sets self.deferred=None and makes the next step illegal
        self.deferred.addErrback(log.err)
    """
    deferred.addCallbacks(callback, errback)
    deferred.addErrback(log.err)


if __name__ == "__main__":
    """Demo using a simple echo server.
    """
    port = 2150
    binary = False
            
    if binary:
        testStrings = (
            "foo\nba",
            "r\nfuzzle\nqu",
            "it",
            "\n"
        )
    else:
        testStrings = (
            "string with 3 nulls: 1 \0 2 \0 3 \0 end",
            "string with 3 quoted nulls: 1 \\0 2 \\0 3 \\0 end",
            '"quoted string followed by carriage return"\r',
            '',
            "string with newline: \n end",
            "string with carriage return: \r end",
            "quit",
        )
    
    strIter = iter(testStrings)

    def runTest():
        try:
            testStr = strIter.next()
            print "Client writing %r" % (testStr,)
            if binary:
                clientSocket.write(testStr)
            else:
                clientSocket.writeLine(testStr)
            Timer(0.001, runTest)
        except StopIteration:
            pass

    def clientRead(sock):
        if binary:
            outStr = sock.read()
        else:
            outStr = sock.readLine()
        print "Client read    %r" % (outStr,)
        if outStr and outStr.strip() == "quit":
            print "*** Data exhausted; closing the client connection"
            clientSocket.close()

    def clientState(sock):
        state, reason = sock.fullState
        if reason:
            print "Client %s: %s" % (state, reason)
        else:
            print "Client %s" % (state,)
        if sock.isDone:
            print "*** Client closed; now closing the server"
            echoServer.close()
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
        elif server.isDone:
            print "*** Halting the reactor"
            reactor.stop()

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
            readLine = sock.readLine(default=None)
            if readLine is not None:
                sock.writeLine(readLine)

    print "*** Starting echo server on port %s; binary=%s" % (port, binary)
    echoServer = EchoServer(port = port, stateCallback = serverState)

    reactor.run()
