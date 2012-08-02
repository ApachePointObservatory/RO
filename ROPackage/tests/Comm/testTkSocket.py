# -*- test-case-name: tests.Comm.testTkSocket -*-
import Tkinter
from twisted.trial import unittest
from twisted.internet.defer import Deferred
import twisted.internet.tksupport
from twisted.internet import reactor
from RO.Comm.TkSocket import TCPSocket, TCPServer

root = Tkinter.Tk()

Port = 2210

class TestRunner(object):
    def __init__(self, sendRcvList, binaryServer=False):
        self.binaryServer = bool(binaryServer)
        self.sendRcvListIter = iter(sendRcvList)
        self.deferred = Deferred()
        self.endState = None
        self.clientSocket = None
        self.serverSocket = None
        self.echoServer = TCPServer(
            port = Port,
            stateCallback = self.echoState,
            sockReadCallback = self.echoSocketRead,
            sockStateCallback = self.echoSocketState,
            name = "echo",
        )
    
    @property
    def isDone(self):
        return self.endState is not None
    
    def close(self):
        if self.clientSocket:
            self.clientSocket.close()
        if self.serverSocket:
            self.serverSocket.close()
        self.echoServer.close()
    
    def endIfDone(self):
        if self.endState is not None:
            if self.clientSocket and self.clientSocket.isDone \
                and self.serverSocket and self.serverSocket.isDone \
                and self.echoServer.isDone:
                isOK, reason = self.endState
                # remove reference to deferred, for paranoia
                deferred, self.deferred = self.deferred, None
                if isOK:
                    deferred.callback(reason)
                else:
                    deferred.errback(reason)
    
    def clientState(self, sock):
        if sock.isReady:
            self.writeNext()
        elif sock.isDone and not self.isDone:
            self.end(False, "Client socket failed")
        self.endIfDone()

    def clientRead(self, sock):
        if self.readLine:
            data = sock.readLine()
        else:
            data = sock.read()
        if data != self.readData:
            self.deferred.errback(
                "Expected %r but read %r; readLine=%r" % (self.readData, data, self.readLine),
            )
        else:
            self.writeNext()
    
    def echoState(self, server):
        if server.isReady:
            self.makeClient()
        elif server.isDone and not self.isDone:
            self.end(False, "Echo server failed")
        self.endIfDone()
    
    def echoSocketState(self, sock):
        self.serverSocket = sock
        self.endIfDone()
    
    def echoSocketRead(self, sock):
        if self.binaryServer:
            data = sock.read()
            if data is not None:
                sock.write(data)
        else:
            data = sock.readLine(default=None)
            if data is not None:
                sock.writeLine(data)
    
    def end(self, isOK, reason=None):
        self.endState = (isOK, reason)
        self.close()
    
    def makeClient(self):
        self.clientSocket = TCPSocket(
            host = "localhost",
            port = Port,
            stateCallback = self.clientState,
            readCallback = self.clientRead,
            name = "client",
        )

    def writeNext(self):
        try:
            writeData, writeLine, self.readData, self.readLine = self.sendRcvListIter.next()
        except StopIteration:
            self.end(isOK=True)
            return

        if writeData is not None:
            if writeLine:
                self.clientSocket.writeLine(writeData)
            else:
                self.clientSocket.write(writeData)

        if self.readData is None:
            self.writeNext()


class TestTkSocket(unittest.TestCase):
    def setUp(self):
        twisted.internet.tksupport.install(root)

    def tearDown(self):
        twisted.internet.tksupport.uninstall()
    
    def testText(self):
        sendRcvList = (
            ("foo", True, "foo", True),
            ("bar\nbaz", True, "bar", True), # split by the echo server into two replies
            (None, True, "baz", True),
            ("two ", False, None, False),
            ("writes", True, "two writes", True),
            ("binary\r\n", False, "binary\r\n", False),
            ("alt end\n", False, "alt end\r\n", False), # server is line-oriented, so returns correct \r\n
            ("alt end 2\r", False, "alt end 2\r\n", False),
            ("two lines\nin one write", True, "two lines", True),
            (None, True, "in one write", True),
        )
        self.testRunner = TestRunner(sendRcvList)        
        return self.testRunner.deferred

    def testBinaryServer(self):
        sendRcvList = (
            ("foo", True, "foo", True),
            ("bar\nbaz", True, "bar", True), # split by the client into two replies
            (None, True, "baz", True),
            ("two ", False, None, False),
            ("writes", True, "two writes", True),
            ("binary\r\n", False, "binary\r\n", False),
            ("alt end\n", False, "alt end\n", False),
            ("alt end 2\r", False, "alt end 2\r", False),
            ("no line ending", False, "no line ending", False),
            ("two lines\nin one write", True, "two lines", True),
            (None, True, "in one write", True),
        )
        testRunner = TestRunner(sendRcvList, binaryServer=True)
        return testRunner.deferred
