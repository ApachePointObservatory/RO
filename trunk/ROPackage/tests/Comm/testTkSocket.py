# -*- test-case-name: tests.Comm.testTkSocket -*-
import Tkinter

from twisted.trial import unittest
from twisted.internet.defer import Deferred
import twisted.internet.tksupport

root = Tkinter.Tk()
twisted.internet.tksupport.install(root)

import twisted.internet
reactor = twisted.internet.reactor

from RO.Comm.TkSocket import TkSocket, TCPServer
from RO.TkUtil import Timer

Port = 2210

class TestRunner(object):
    def __init__(self, sendRcvList, binary=False):
        self.binary = bool(binary)
        self.sendRcvListIter = iter(sendRcvList)
        self.deferred = Deferred()
        self.isDone = False
        self.clientSocket = None
        self.echoServer = TCPServer(
            port = Port,
            stateCallback = self.echoState,
            sockReadCallback = self.echoRead,
            name = "echo",
        )
    
    def clientState(self, sock):
        if sock.isReady:
            self.writeNext()
        elif sock.isDone and not self.isDone:
            self.end(False, "Client socket failed")

    def clientRead(self, sock):
        if self.readLine:
            data = sock.readLine()
        else:
            data = sock.read()
        if data != self.readData:
            self.deferred.errback(
                "Expected %r but read %r with readLine=%r" % (self.readData, data, self.readLine),
            )
        else:
            self.writeNext()
    
    def echoState(self, echoServer):
        if echoServer.isReady:
            self.makeClient()
        elif echoServer.didFail and not self.isDone:
            self.end(False, "Echo server failed")
    
    def echoRead(self, sock):
        data = sock.readLine(default=None)
        if data is not None:
            sock.writeLine(data)
    
    def end(self, isOK, reason):
        print "end(isOK=%s, reason=%s)" % (isOK, reason)
        if not self.isDone:
            self.isDone = True
            self.echoServer.close()
            if self.clientSocket:
                self.clientSocket.close()
            
            if isOK:
                self.deferred.callback(reason)
            else:
                self.deferred.errback(reason)
    
    def makeClient(self):
        self.clientSocket = TkSocket(
            addr = "localhost",
            port = Port,
            binary = self.binary,
            stateCallback = self.clientState,
            readCallback = self.clientRead,
            name = "client",
        )

    def writeNext(self):
        try:
            writeData, writeLine, self.readData, self.readLine = self.sendRcvListIter.next()
        except StopIteration:
            self.deferred.callback(None)
            return

#        print "writeNext; writeData=%r, writeLine=%r, readData=%r, readLine=%r" % \
#             (writeData, writeLine, self.readData, self.readLine)
        if writeData is not None:
            if writeLine:
                self.clientSocket.writeLine(writeData)
            else:
                self.clientSocket.write(writeData)


class TestTkSocket(unittest.TestCase):
    def testLine(self):
        sendRcvList = (
            ("foo", True, "foo", True),
            ("bar\nbaz", True, "bar", True), # becomes two lines
            (None, True, "baz", True),
        )
        testRunner = TestRunner(sendRcvList)        
        return testRunner.deferred


if __name__ == "__main__":
    def foo(reason):
        print "End with reason =", reason
        reactor.stop()
        
    tc = TestTkSocket()
    d = tc.testLine()
    d.addBoth(foo)
    
    reactor.run()
