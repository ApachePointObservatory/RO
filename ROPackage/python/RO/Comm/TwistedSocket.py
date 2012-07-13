#!/usr/bin/env python
"""Socket wrapper that works with the Twisted framework

The intention is to work with TCPConnection and all the infrastructure that uses it.

TO DO: rewrite the test code and try it out.
Also: try to find out how to query a protocol or transport to see if it is alive.

History:
2012-07-11 ROwen    First cut, based on TwistedSocket
"""
__all__ = ["TwistedSocket", "TwistedServer", "TCP4Server"]
import sys
import traceback
from BaseSocket import BaseSocket, BaseServer, nullCallback
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet import reactor

class _Socket(LineReceiver):
    def __init__(self):
        self._readCallback = nullCallback
        self._connectionLostCallback = nullCallback
    
    def roSetCallbacks(self, readCallback, connectionLostCallback):
        """Add TwistedSocket-specific callbacks
        
        Inputs:
        - readCallback: a function that receives one argument: the read data
        - connectionLostCallback: a function that receives one argument: the reason
            (a Twisted reason object; defaults to Twisted's connectionDone)
        """
        self._readCallback = readCallback
        self._connectionLostCallback = connectionLostCallback
    
    def lineReceived(self, data):
        self._readCallback(data)
    
    def connectionMade(self):
#        print "%s.connectionMade(); self.factory._connectionMadeCallback=%s" % (self, self.factory._connectionMadeCallback)
        self.factory._connectionMadeCallback(self)
    
    def connectionLost(self, reason):
#         print "%s.connectionLost(%s); self._connectionLostCallback=%s" % (self, reason, self._connectionLostCallback)
        self._connectionLostCallback(reason)
    
    def roAbort(self):
        """Discard callbacks and abort the connection
        """
#         print "%s.roAbort()" % (self,)
        self._readCallback = nullCallback
        self._connectionLostCallback = nullCallback
        if self.transport:
            self.transport.abortConnection()
    
class _SocketFactory(Factory):
    protocol = _Socket
    
    def __init__(self, connectionMadeCallback = nullCallback):
        self._connectionMadeCallback = connectionMadeCallback


class TwistedSocket(BaseSocket):
    """A basic TCP/IP socket using Twisted framework.
    
    Inputs:
    - endpoint  a Twisted endpoint, e.g. twisted.internet.endpoints.TCP4ClientEndpoint;
    - protocol: a Twisted protocol;
        you must either specify endpoint or protocol, but not both
    - state     the initial state
    - readCallback: function to call when data read; receives: self
    - stateCallback a state callback function; see addStateCallback for details
    """
    def __init__(self,
        endpoint = None,
        protocol = None,
        state = BaseSocket.Connected,
        readCallback = nullCallback,
        stateCallback = nullCallback,
        name = "",
    ):
#         print "TwistedSocket(name=%r, endpoint=%r, protocol=%r, state=%r, readCallback=%r, stateCallback=%r)" % \
#             (name, endpoint, protocol, state, readCallback, stateCallback)
        if bool(endpoint is None) == bool(protocol is None):
            raise RuntimeError("Must provide one of endpoint or protocol")
        self._endpoint = endpoint
        self._endpointDeferred = None
        self._protocol = None
        self._data = None
        BaseSocket.__init__(self,
            state = state,
            readCallback = readCallback,
            stateCallback = stateCallback,
            name = name
        )
        if protocol is not None:
            self._connectionMade(protocol)
        else:
            self._setState(BaseSocket.Connecting)
            self._endpointDeferred = self._endpoint.connect(_SocketFactory())
            self._endpointDeferred.addCallbacks(self._connectionMade, self._connectionFailed)

    def _clearCallbacks(self):
        """Clear any callbacks added by this class. Called just after the socket is closed.
        """
        BaseSocket._clearCallbacks(self)
        self._connCallback = None
        if self._endpointDeferred is not None:
            self._endpointDeferred.cancel()
        if self._protocol is not None:
            self._protocol.roAbort()

    def _connectionFailed(self, err):
        """Connection failed callback
        """
#         print "%s._connectionFailed(%s)" % (self, err)
        reasonStr = str(err) if err is not None else None
        if self._state == BaseSocket.Closing:
            self._setState(BaseSocket.Closed, reasonStr)
        else:
            self._setState(BaseSocket.Failed, reasonStr)
        return err
    
    def _connectionMade(self, protocol):
        """Callback when connection made
        """
#         print "%s._connectionMade(%r); sockStateCallback=%s" % (self, protocol, self._sockStateCallback)
        self._protocol = protocol
        self._protocol.roSetCallbacks(
            readCallback = self._doRead,
            connectionLostCallback = self._connectionFailed,
        )
#         print "%s: setting state to Connected" % (self,)
        self._setState(BaseSocket.Connected)

    def _basicClose(self):
        """Close the socket.
        """
        self._protocol.transport.loseConnection()
    
    def readLine(self, default=None):
        """Read one line of data.
        Do not return the trailing newline.
        If a full line is not available, return default.
        
        Inputs:
        - default   value to return if a full line is not available
                    (in which case no data is read)
        
        Raise RuntimeError if the socket is not connected.
        """
        if self._data is None:
            return default

        data, self._data = self._data, None
        return data
    
    def write(self, data):
        """Write data to the socket. Does not block.
        
        Safe to call as soon as you call connect, but of course
        no data is sent until the connection is made.
        
        Raises UnicodeError if the data cannot be expressed as ascii.
        Raises RuntimeError if the socket is not connecting or connected.
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
#         print "write(%r)" % (data,)
        if self._state not in (self.Connected, self.Connecting):
            raise RuntimeError("%s not connected" % (self,))
        self.protocol.send(data)
    
    def writeLine(self, data):
        """Write a line of data terminated by standard newline
        (which for the net is \r\n, but the socket's auto newline
        translation takes care of it).
        """
#         print "writeLine(%r)" % (data,)
        if self._state != self.Connected:
            raise RuntimeError("%s not connected" % (self,))
        self._protocol.sendLine(data)
    
    def _doRead(self, data):
        """Called when there is data to read"""
#         print "%s _doRead" % (self,)
        if self._data != None:
            print "%s: Warning: data lost" % (self,)
        self._data = data
        if self._readCallback:
            try:
                self._readCallback(self)
            except Exception, e:
                sys.stderr.write("%s read callback %s failed: %s\n" % (self, self._readCallback, e,))
                traceback.print_exc(file=sys.stderr)

    def __str__(self):
        return "TwistedSocket(name=%r)" % (self._name)

class TwistedServer(BaseServer):
    """A tcp socket server
    
    Note: this could have state, but presently does not
    """
    def __init__(self,
        endpoint,
        connCallback = nullCallback,
        stateCallback = nullCallback,
        sockReadCallback = nullCallback,
        sockStateCallback = nullCallback,
        name = "",
    ):
        """Construct a socket server
        
        Inputs:
        - endpoint: a Twisted endpoint, e.g. twisted.internet.endpoints.TCP4ClientEndpoint
        - connCallback: function to call when a client connects; it receives the following arguments:
                    - sock, a TwistedSocket
        - stateCallback: function to call when server changes state; it receives one argument: this server
        - sockReadCallback: function for each server socket to call when it receives data;
            See BaseSocket.addReadCallback for details
        - sockStateCallback: function for each server socket to call when it receives data
            See BaseSocket.addStateCallback for details
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
        self._endpointDeferred = self._endpoint.listen(_SocketFactory(self._newConnection))
        self._endpointDeferred.addCallbacks(self._listeningCallback, self._connectionFailed)
        self._numConn = 0
    
    def _listeningCallback(self, protocol):
        self._protocol = protocol
        self._setState(self.Listening)

    def _basicClose(self):
        """Shut down the server.
        """
        if self._protocol is not None:
            self._closeDeferred = self._protocol.stopListening()
            self._closeDeferred.addBoth(self._connectionFailed)
    
    def _clearCallbacks(self):
        """Clear any callbacks added by this class. Called just after the socket is closed.
        """
        BaseServer._clearCallbacks(self)
        self._connCallback = nullCallback
        if self._endpointDeferred:
            self._endpointDeferred.cancel()
        if self._closeDeferred:
            self._closeDeferred.cancel()
    
    def _connectionFailed(self, err):
        """Connection failed callback
        """
#         print "%s._connectionFailed(%s)" % (self, err)
        reasonStr = str(err) if err is not None else None
        if self._state == BaseSocket.Closing:
            self._setState(BaseSocket.Closed, reasonStr)
        else:
            self._setState(BaseSocket.Failed, reasonStr)
        return err
    
    def _newConnection(self, protocol):
        """A client has connected. Create a TwistedSocket and call the connection callback with it.
        """
#         print "TwistedServer._newConnection(%r)" % (protocol,)
        self._numConn += 1
        newSocket = TwistedSocket(
            protocol = protocol,
            readCallback = self._sockReadCallback,
            stateCallback = self._sockStateCallback,
            name = "%s%d" % (self._name, self._numConn,)
        )

        try:
            self._connCallback(newSocket)
        except Exception, e:
            errMsg = "%s connection callback %s failed: %s" % (self.__class__.__name__, self._connCallback, e)
            sys.stderr.write(errMsg + "\n")
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    """Demo using a simple echo server.
    """
    from twisted.internet.endpoints import TCP4ServerEndpoint
    from RO.TwistedUtil import Timer
    
    port = 2150

    testStrings = (
        "foo",
        "string with 3 nulls: 1 \0 2 \0 3 \0 end",
        "string with 3 quoted nulls: 1 \\0 2 \\0 3 \\0 end",
        '"quoted string followed by carriage return"\r',
        "string with newline: \n end",
        "string with carriage return: \r end",
         "quit",
    )
    
    strIter = iter(testStrings)
    
    clientSocket = None

    def runTest():
        try:
            testStr = strIter.next()
            print "Client writing %r" % (testStr,)
            clientSocket.writeLine(testStr)
            Timer(0.5, runTest)
        except StopIteration:
            pass

    def clientRead(sock):
        outStr = sock.readLine()
        print "Client read   %r" % (outStr,)
        if outStr == "quit":
            print "*** Data exhausted; closing the client connection"
            clientSocket.close()

    def clientState(sock):
        stateVal, stateStr, reason = sock.getFullState()
        if reason:
            print "Client %s: %s" % (stateStr, reason)
        else:
            print "Client %s" % (stateStr,)
        if sock.isDone:
            print "*** Client closed; now halting reactor (which kills the server)"
            reactor.stop()
        if sock.isReady:
            print "*** Client connected; now sending test data"
            runTest()

    def serverState(server):
        global clientSocket
        stateVal, stateStr, reason = server.getFullState()
        if reason:
            print "Server %s: %s" % (stateStr, reason)
        else:
            print "Server %s" % (stateStr,)
        if server.isReady:
            print "*** Echo server ready; now starting up a client"
    
            endpoint = TCP4ClientEndpoint(reactor, host="localhost", port=port)
            clientSocket = TwistedSocket(
                endpoint = endpoint,
                stateCallback = clientState,
                readCallback = clientRead,
                name = "client",
            )

    class EchoServer(TwistedServer):
        def __init__(self, port, stateCallback):
            endpoint = TCP4ServerEndpoint(reactor, port=port)
            TwistedServer.__init__(self,
                endpoint = endpoint,
                stateCallback = stateCallback,
                sockReadCallback = self.sockReadCallback,
                name = "echo",
            )
        def sockReadCallback(self, sock):
            readLine = sock.readLine()
            sock.writeLine(readLine)

    print "*** Starting echo server on port", port
    echoServer = EchoServer(port = port, stateCallback = serverState)

    reactor.run()
