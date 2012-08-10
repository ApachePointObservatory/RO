#!/usr/bin/env python
"""Sockets optimized for use with Tkinter GUIs.

TkSocket allows nonblocking event-driven operation:
- Connection and disconnection are done in the background.
- You may begin writing as soon as you start connecting.
- Written data is queued and sent as the connection permits.
- The read and readLine methods are nonblocking.
- You may specify a read callback, which is called when data is available,
  and a state callback, which is called when the connection state changed.


History:
2002-11-22 ROwen    First version
2003-02-25 ROwen    Bug fix: could hang on program exit; cured using atexit;
                    also added a __del__ method for the same reason.
2003-02-27 ROwen    _WriteThread.close was printing an error message
                    instead of terminating the write thread.
2003-04-04 ROwen    Bug fix: BasicSocket was being set to a function instead of a type;
                    this failed under Windows (hanks to Craig Loomis for report and fix).
2003-05-01 ROwen    Modified to work with Python 2.3b1 (which does not support
                    _tkinter.create/deletefilehandler); thanks to Martin v. Lowis for the fix.
2003-10-13 ROwen    Overhauled to more robust and to prevent delays while connecting.
                    Also added support for monitoring state.
2003-10-14 ROwen    Bug fix: close while NotConnected caused perpetual Closing state.
2003-11-19 ROwen    Bug fix: reason was not always a string; modified _setState
                    to cast it to a string.
2003-12-04 ROwen    Modified to only call the state callback when the state or reason changes.
2004-05-18 ROwen    Increased state polling delay from 100ms to 200ms.
                    Stopped importing sys since it was not being used.
2004-07-21 ROwen    Overhauled to add Windows compatibility, by eliminating the use
                    of createfilehandler. Modified to use tcl sockets,
                    eliminating all use of threads. Visible changes include:
                    - TCP/IP is the only type of socket.
                    - The socket is connected when it is created.
                    - The read callback no longer receives the data read;
                      call read or readLine as appropriate.
                    - The state Closing is gone; when a socket begins closing
                      the state is set to Closed and there is no way to tell
                      when the close finishes (due to limitations in tcl sockets)
                    - Any data queued for write is written before closing finishes.
2004-10-12 ROwen    Fixed documentation for setReadCallback.
                    Removed class attribute _tkWdg since it was not being used.
2005-06-08 ROwen    Changed TkSocket and NullSocket to new-style classes.
2005-06-14 ROwen    Modified to clear references to the following when the socket closes,
                    to aid garbage collection:
                    - read and state callback functions
                    - pointer to the tk socket
                    - pointer to a string var and its _tk
2005-06-16 ROwen    Removed an unused variable (caught by pychecker).
2005-08-05 ROwen    Modified to use _tk.call instead of _tk.eval for config (because I expect it to
                    handle quoting arguments better and I was able to cut down the number of calls).
2005-08-10 ROwen    Bug fix: was not sending binary data through correctly.
                    Fixed by using _tk.call instead of _tk.eval to write.
                    Modified to use call instead of eval in all cases.
                    Added TkServerSocket and TkBaseSocket.
                    Changed state constants from module constants to class constants.
2005-08-22 ROwen    TkSocket: bug fix: an exception could occur in the read
                    callback if the remote host closed the connection.
                    Formerly the internal socket read callback tried to check
                    the connection before calling the user's read callback,
                    but that test could fail due to timing issues.
                    Now the user's read callback is always called
                    and read and readLine always return "" (or default for readLine)
                    if the socket is closed -- they never raise an exception.
                    Bug fix: Bug fix: _TkCallback was creating a tk function name
                    that was not necessarily unique, which could lead to subtle bugs
                    (tk not being calling some callback functions).
                    Eliminated the unused self._tkVar.
2005-08-24 ROwen    Bug fix: leaked tcl functions.
                    Modified to use TkUtil.TclFunc instead of an local _TkCallback.
2006-07-10 ROwen    Modified BaseServer to be compatible with Python 2.3.
                    Added BaseServer to __all__.
                    Bug fix: invalid import in test code.
2008-01-16 ROwen    TkSocket: added pre-test for socket existing to write and writeLine.
2008-03-06 ROwen    Stopped setting instance variable _prevLine; it was not used anywhere.
2010-06-28 ROwen    Modified to require Python 2.4 by assuming set is a builtin type.
2011-06-16 ROwen    Ditched obsolete "except (SystemExit, KeyboardInterrupt): raise" code.
2012-08-01 ROwen    - Renamed TkServerSocket to TCPServer and added BaseServer functionality.
                    - Renamed TkSocket to TCPSocket.
                    - Many methods are now properties, e.g. isDone->isDone.
                    - Eliminated the binary argument to TCLSocket and tcl end-of-line translation;
                      instead writeLine always appends \r\n and readLine breaks on any of \r\n, \n or \r.
                    - Removed BaseServer; use TCPServer instead.
                    - Modified to use base classes from the BaseSocket module.
                    - Modified example code to use RO.TkUtil.Timer.
                    - Improved the behavior of readLine and writeLine when binary=True.
"""
__all__ = ["TCPSocket", "TCPServer", "TkSocket", "TkServerSocket"]

import re
import sys
import traceback
import Tkinter
import RO.TkUtil
from RO.Comm.BaseSocket import BaseSocket, BaseServer, nullCallback

class _TkSocketWrapper(object):
    """Convenience wrapper around a Tk socket
    """
    def __init__(self,
        tkSock = None,
        sockArgs = None,
        name = "",
    ):
        """Create a _TkSocketWrapper
    
        Inputs:
        - tkSock    the tk socket connection; if not None then sockArgs is ignored
        - sockArgs  argument list for tk socket; ignored if tkSock not None
        - name      a string to identify this socket; strictly optional
        """
        self.name = name
        self._tkSocket = None
        # dictionary of typeStr:tclFunc, where:
        # typeStr is one of "readable" or "writable"
        # tclFunc is a tcl-wrapped function, an instance of RO.TkUtil.TclFunc
        self._callbackDict = dict()
        self._readVar = Tkinter.StringVar()
        self._tk = self._readVar._tk

        if tkSock:
            self._tkSocket = tkSock
        elif sockArgs:
            try:
                self._tkSocket = self._tk.call('socket', *sockArgs)
            except Tkinter.TclError, e:
                raise RuntimeError(e)
        else:
            raise RuntimeError("Must specify tkSock or sockArgs")

        try:
            configArgs = (
                '-blocking', 0,
                '-buffering', 'none',
                '-encoding', 'binary',
                '-translation', 'binary',
            )
            
            #print "name=%s, configArgs=%s" % (name, configArgs)
            self._tk.call('fconfigure', self._tkSocket, *configArgs)
        except Tkinter.TclError, e:
            raise RuntimeError(e)

    @property
    def isOKReason(self):
        """Return isOK, reason
        
        Returns:
        - True, "" if OK
        - False, errStr if an error
        - True, reason if closed without error; reason may be ""
        """
        #print "%s.isOKReason()" % (self,)
        errStr = self._tk.call('fconfigure', self._tkSocket, '-error')
        if errStr:
            return False, errStr
        isEOFStr = self._tk.call('eof', self._tkSocket)
        if int(isEOFStr):
            return True, "closed by remote host"
        return True, ""

    def close(self):
        """Close the socket.
        """
        if self._tkSocket:
            try:
                # close socket (this automatically deregisters any file events)
                self._tk.call('close', self._tkSocket)
            except Exception:
                pass
            self._tkSocket = None
        self._tk = None
    
    def clearCallbacks(self):
        """Clear any callbacks added by this class.
        Called just after the socket is closed.
        """
        for tclFunc in self._callbackDict.itervalues():
            tclFunc.deregister()
        self._callbackDict = dict()
    
    def setCallback(self, callFunc=None, doWrite=False):
        """Set, replace or clear the read or write callback.

        Inputs:
        - callFunc  the new callback function, or None if none
        - doWrite   if True, a write callback, else a read callback
        """
        #print "%s.setCallback(callFunc=%s, doWrite=%s)" % (self, callFunc, doWrite)
        if doWrite:
            typeStr = 'writable'
        else:
            typeStr = 'readable'
        
        if callFunc:
            tclFunc = RO.TkUtil.TclFunc(callFunc)
            tkFuncName = tclFunc.tclFuncName
        else:
            tclFunc = None
            tkFuncName = ""
        
        try:
            self._tk.call('fileevent', self._tkSocket, typeStr, tkFuncName)
        except Tkinter.TclError, e:
            if tclFunc:
                tclFunc.deregister()
            raise RuntimeError(e)

        # deregister and dereference existing tclFunc, if any
        oldCallFunc = self._callbackDict.pop(typeStr, None)
        if oldCallFunc:
            oldCallFunc.deregister()

        # Save a reference to the new tclFunc,, if any
        if tclFunc:
            self._callbackDict[typeStr] = tclFunc
    
    def read(self):
        """Read data from the socket. Do not block.
        """
        return self._tk.call('read', self._tkSocket)        
    
    def write(self, data):
        """Write data to the socket. Do not block.
        
        The data is queued if the socket is not yet connected.
        The behavior is undefined if the socket has errors or has disconnected.
        
        Raises UnicodeError if the data cannot be expressed as ascii.
        
        An alternate technique (from Craig):
        turn } into \}; consider escaping null and all but
        the final \n in the same fashion
        (to do this it probably makes sense to supply a writeLine
        that escapes \n and \r and then appends \n).
        Then:
        self._tk.eval('puts -nonewline %s { %s }' % (self._tkSocket, escData))
        """
        #print "%s.write(data=%r)" % (self, data)
        self._tk.call('puts', '-nonewline', self._tkSocket, data)

    def __del__(self):
        """At object deletion, make sure the socket is properly closed.
        """
        if self._tk is not None:
            self.clearCallbacks()
            self.close()

    def __str__(self):
        return "%s(name=%s)" % (self.__class__.__name__, self.name)


class TCPSocket(BaseSocket):
    """A TCP/IP socket that reads and writes using Tk events.
    """
    lineEndPattern = re.compile("\r\n|\r|\n")
    def __init__(self,
        host,
        port,
        readCallback = nullCallback,
        stateCallback = nullCallback,
        tkSock = None,
        name = "",
    ):
        """Construct a TCPSocket
    
        Inputs:
        - host      IP address as dotted name or dotted numbers
        - port      IP port
        - readCallback  function to call when data read; receives: self
        - stateCallback function to call when state or reason changes; receives: self
        - tkSock    existing tk socket (if missing, one is created and connected)
        - name      a string to identify this socket; strictly optional
        """
        self._host = host
        self._port = port
        self.__buffer = ""
        BaseSocket.__init__(self,
            readCallback = readCallback,
            stateCallback = stateCallback,
            name = name,
        )
        if tkSock is None:
            sockArgs = ('-async', host, port)
        else:
            sockArgs = None
        self._tkSocketWrapper = _TkSocketWrapper(tkSock=tkSock, sockArgs=sockArgs, name=name)
        self._tkSocketWrapper.setCallback(self._doRead, doWrite=False)

        try:
            # add callbacks; the write callback indicates the socket is connected
            # and is just used to detect state
            self._tkSocketWrapper.setCallback(self._doRead, doWrite=False)
            self._tkSocketWrapper.setCallback(self._doConnect, doWrite=True)
        except Tkinter.TclError, e:
            raise RuntimeError(e)
        
        self._setState(self.Connecting)
        self._checkSocket()

    @property
    def host(self):
        return self._host
    
    @property
    def port(self):
        return self._port

    def read(self, nChar=None):
        """Read data. Do not block.
        
        Inputs:
        - nChar: maximum number of chars to return; if None then all available data is returned.
        
        Raise RuntimeError if the socket is not connected.
        """
        if nChar is None:
            data, self.__buffer = self.__buffer, ""
        else:
            data, self._buffer = self._buffer[0:nChar], self._buffer[nChar:]
        #print "%s.read(nChar=%r) returning %r; remaining buffer=%r" % (self, nChar, data, self.__buffer)

        if self.__buffer and self._readCallback:
            RO.TkUtil.Timer(0.000001, self._readCallback, self)
        return data

    def readLine(self, default=None):
        """Read one line of data, not including the end-of-line indicator. Do not block.
        
        Any of \r\n, \r or \n are treated as end of line.
        
        Inputs:
        - default   value to return if a full line is not available
                    (in which case no data is read)
        
        Raise RuntimeError if the socket is not connected.
        """
        res = self.lineEndPattern.split(self.__buffer, 1)
        if len(res) == 1:
            # readDelimiter not found; leave the buffer alone and don't bother to call the callback again
            #print "%s.readLine(default=%r) returning the default; remaining buffer=%r" % (self, default, self.__buffer)
            return default
        self.__buffer = res[1]
        #print "%s.readLine(default=%r) returning %r; remaining buffer=%r" % (self, default, res[0], self.__buffer)

        if self.__buffer and self._readCallback:
            RO.TkUtil.Timer(0.000001, self._readCallback, self)
        return res[0]
    
    def write(self, data):
        """Write data. Do not block.
        
        No end-of-line translation is performed.
        
        Safe to call as soon as you call connect, but of course
        no data is sent until the connection is made.
        
        Raises UnicodeError if the data cannot be expressed as ascii.
        Raises RuntimeError if the socket is not connecting or connected.
        If an error occurs while sending the data, the socket is closed,
        the state is set to Failed and _reason is set.
        """
        #print "%s.write(%r)" % (self, data)
        if self._state not in (self.Connected, self.Connecting):
            raise RuntimeError("%s not connected" % (self,))
        self._tkSocketWrapper.write(data)
        self._assertConn()

    def writeLine(self, data):
        """Write a line of data terminated by standard newline (\r\n). Do not block.
        """
        #print "%s.writeLine(%r)" % (self, data)
        self.write(data + "\r\n")
    
    def _assertConn(self):
        """Check connection; close and raise RuntimeError if not OK.
        """
        if not self._checkSocket():
            raise RuntimeError("%s not connected" % (self,))

    def _basicClose(self):
        """Close the Tk socket.
        """
        self._tkSocketWrapper.close()
        if self._state == self.Closing:
            self._setState(self.Closed)
        else:
            self._setState(self.Failed)
    
    def _checkSocket(self):
        """Check socket for errors.

        Return True if OK.
        Close socket and return False if errors found.
        """
        if self.isDone:
            return False
        isOK, errStr = self._tkSocketWrapper.isOKReason
        if errStr:
            self.close(isOK=isOK, reason=errStr)
            return False
        return True
    
    def _clearCallbacks(self):
        """Clear any callbacks added by this class.
        Called just after the socket is closed.
        """
        BaseSocket._clearCallbacks(self)
        self._tkSocketWrapper.clearCallbacks()
    
    def _doConnect(self):
        """Called when connection made.
        """
        # cancel write handler; it has done its job
        self._tkSocketWrapper.setCallback(callFunc=None, doWrite=True)
        
        if self._checkSocket():
            self._setState(self.Connected)
    
    def _doRead(self, *args):
        newData = self._tkSocketWrapper.read()
        self.__buffer = newData if not self.__buffer else self.__buffer + newData
        #print "_doRead: newData=%r; buffer=%r" % (newData, self.__buffer)
        self._readCallback(self)

    def _getArgStr(self):
        return "name=%r, host=%r, port=%r" % (self.name, self._host, self._port)


class TCPServer(BaseServer):
    """A tcp socket server
    
    Inputs:
    - connCallback  function to call when a client connects; it recieves the following arguments:
                - sock, a TCPSocket
    """
    def __init__(self,
        connCallback = nullCallback,
        port = 0,
        stateCallback = nullCallback,
        sockReadCallback = nullCallback,
        sockStateCallback = nullCallback,
        name = "",
    ):
        """Construct a socket server
        
        Inputs:
        - connCallback: function to call when a client connects; it receives the following arguments:
                    - sock, a Socket
        - port      port number or name of supported service;
                    if 0 then a port is automatically chosen
        - stateCallback: function to call when server changes state; it receives one argument: this server
        - sockReadCallback: function for each server socket to call when it receives data;
            See BaseSocket.setReadCallback for details
        - sockStateCallback: function for each server socket to call when it receives data
            See BaseSocket.addStateCallback for details
        - name: a string to identify this socket; strictly optional
        
        Warning: stateCallback does not get all state changes reliably.
        It gets Listening as soon as the server is created (even though it is not listening yet)
        and the only other notice is closure when close is called.
        """
        self._port = port
        self._connCallback = connCallback

        BaseServer.__init__(self,
            connCallback = connCallback,
            stateCallback = stateCallback,
            sockReadCallback = sockReadCallback,
            sockStateCallback = sockStateCallback,
            name = name,
        )

        self._tkNewConn = RO.TkUtil.TclFunc(self._newConnection)
        sockArgs = (
            '-server', self._tkNewConn.tclFuncName,
            port,
        )
        self._tkSocketWrapper = _TkSocketWrapper(sockArgs=sockArgs, name=name)
        self._setState(BaseServer.Listening)

    @property
    def port(self):
        return self._port

    def _basicClose(self):
        """Close the Tk socket.
        """
        self._tkSocketWrapper.close()
        if self._state == self.Closing:
            self._setState(self.Closed)
        else:
            self._setState(self.Failed)

    def _clearCallbacks(self):
        """Clear any callbacks added by this class.
        Called just after the socket is closed.
        """
        BaseServer._clearCallbacks(self)
        self._tkSocketWrapper.clearCallbacks()
        self._tkNewConn.deregister()
        self._tkNewConn = None
    
    def _newConnection(self, tkSock, clientAddr, clientPort):
        """A client has connected. Create a TCPSocket and call the connection callback with it.
        """
        newSocket = TCPSocket(
            tkSock = tkSock,
            host = clientAddr,
            port = clientPort,
            readCallback = self._sockReadCallback,
            stateCallback = self._sockStateCallback,
            name = self.name,
        )
        
        try:
            self._connCallback(newSocket)
        except Exception, e:
            errMsg = "%s connection callback %s failed: %s" % (self, self._connCallback, e)
            sys.stderr.write(errMsg + "\n")
            traceback.print_exc(file=sys.stderr)

    def _getArgStr(self):
        return "name=%r, port=%r" % (self.name, self._port)


if __name__ == "__main__":
    """Demo using a simple echo server.
    """
    root = Tkinter.Tk()
    root.withdraw()
    from RO.TkUtil import Timer
    
    port = 2150
    binary = True
            
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
            print "*** Halting the tcl event loop"
            root.quit()

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
    
    root.mainloop()
