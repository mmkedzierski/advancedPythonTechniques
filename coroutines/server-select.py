from datetime import datetime
from datetime import timedelta
from urlparse import urlparse
import hashlib
import os
import random
import select
import socket
import traceback

debugDispatch = True

CHUNK_SIZE = 1024
CACHE_VALIDITY = timedelta(seconds=60)
PORT = 1000 + int(hashlib.md5(os.environ['USER']).hexdigest()[:4], 16) % 64536

class READABLE: pass 
class WRITABLE: pass


def ts():
    return datetime.now().strftime('%Y-%m-%d:%H:%M:%S')

def parseDownRequest(request):
    url = urlparse(request)
    assert url.scheme == 'http'
    assert url.hostname is not None
    assert url.path is not None
    port = 80
    if url.port: port = url.port
    return url.hostname, port, url.path

class RequestHandler:
    def __init__(self):
        self.downConnSocket = None
        self.downAddr = None
        self.requestLineAcc = []
        self.upRequest = None
        self.upResponseMD5Hasher = None
        self.upHost = None
        self.upPort = None
        self.upPath = None
    
    def accept(self, downSocket):
        self.downConnSocket, self.downAddr = downSocket.accept()
        print ts(), "accepted connection from %s:%s" % self.downAddr
        theReactor.on(self.downConnSocket, READABLE, self.recvDownRequest)
    
    def recvDownRequest(self):
        chunk = self.downConnSocket.recv(CHUNK_SIZE)
        if chunk:
            for ch in chunk:
                if ch == '\n':
                    line = ''.join(self.requestLineAcc).strip()
                    self.requestLineAcc = []
                    self.handleDownRequestLine(line)
                else:
                    self.requestLineAcc.append(ch)
        else:
            line = ''.join(self.requestLineAcc).strip()
            self.requestLineAcc = []
            if line:
                self.handleDownRequestLine(line)
            else:
                self.close()
    
    def handleDownRequestLine(self, downRequestLine):
        if not downRequestLine:
            theReactor.on(self.downConnSocket, READABLE, self.recvDownRequest)
            return

        print ts(), '[%s:%s]' % self.downAddr, 'handling', repr(downRequestLine)
        
        upHost, upPort, upPath = parseDownRequest(downRequestLine)
        self.upHost, self.upPort, self.upPath = upHost, upPort, upPath
        
        if (upHost, upPort, upPath) in theCache:
       	     timestamp, downResponse = theCache[(upHost, upPort, upPath)]
    	     if datetime.now() - timestamp <= CACHE_VALIDITY:
    	          self.downResponse = downResponse
    	          theReactor.on(self.downConnSocket, WRITABLE,
    	              self.sendDownResponse)
    	          return
        
        self.upSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print ts(), '[%s:%s]' % self.downAddr, \
            'connecting to %s:%s' % (upHost, upPort)
        self.upSocket.connect((upHost, upPort))
        self.upRequest = 'GET ' + upPath + ' HTTP/1.0\n\n'
        
        theReactor.on(self.upSocket, WRITABLE, self.sendUpRequest)
    
    def sendUpRequest(self):
        if self.upRequest:
            sizeSent = self.upSocket.send(self.upRequest)
            self.upRequest = self.upRequest[sizeSent:]
            theReactor.on(self.upSocket, WRITABLE, self.sendUpRequest)
        else:
            self.upResponseMD5Hasher = hashlib.md5()
            theReactor.on(self.upSocket, READABLE, self.recvUpResponse)
    
    def recvUpResponse(self):
        chunk = self.upSocket.recv(CHUNK_SIZE)
        if chunk:
            self.upResponseMD5Hasher.update(chunk)
            theReactor.on(self.upSocket, READABLE, self.recvUpResponse)
        else:
            self.upSocket.close()
            print ts(), '[%s:%s]' % self.downAddr, \
                'closing upstream connection'
            self.upSocket = None
            self.downResponse = self.upResponseMD5Hasher.hexdigest() + '\n'
            cacheKey = (self.upHost, self.upPort, self.upPath)
            theCache[cacheKey] = (datetime.now(), self.downResponse)
            theReactor.on(self.downConnSocket, WRITABLE, self.sendDownResponse)
                
    def sendDownResponse(self):
        if self.downResponse:
            sizeSent = self.downConnSocket.send(self.downResponse)
            self.downResponse = self.downResponse[sizeSent:]
            theReactor.on(self.downConnSocket, WRITABLE, self.sendDownResponse)
        else:
            theReactor.on(self.downConnSocket, READABLE, self.recvDownRequest)
            
    def close(self):
        if self.downConnSocket is not None: 
            self.downConnSocket.close()
            print ts(), "closing connection from %s:%s" % self.downAddr
        if self.upSocket is not None: self.upSocket.close()
    
    def __repr__(self):
        return '<RequestHandler [%s:%s]>' % self.downAddr


def stdErrHandler(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback)

class Reactor:
    def __init__(self):
        self.continuations = { READABLE: {}, WRITABLE: {} }
        
    def on(self, sock, mode, continuation):
        assert mode in [READABLE, WRITABLE]
        fd = sock.fileno()
        assert fd not in self.continuations[mode]
        self.continuations[mode][fd] = continuation
    
    def dispatch(self):
        readWatches = self.continuations[READABLE].keys()
        writeWatches = self.continuations[WRITABLE].keys()
        if debugDispatch:
            print ts(), "server about to call select(), continuations:"
            self.showContinuations()
        readables, writables, _ = select.select(readWatches, writeWatches, [])
        readables = map(lambda fd: (fd, READABLE), readables)
        writables = map(lambda fd: (fd, WRITABLE), writables)
        fd, mode = random.choice(readables + writables)
        continuation = self.continuations[mode][fd]
        del self.continuations[mode][fd]
        if debugDispatch:
            print ts(), "selected continuation", \
                {READABLE: 'RD', WRITABLE: 'WR'}[mode], \
                fd, continuation.__name__
        try:
            continuation()
        except Exception:
            traceback.print_exc()
    
    def run(self):
        while self.continuations[READABLE] or self.continuations[WRITABLE]:
            self.dispatch()
    
    def showContinuations(self):
        for fd, cont in self.continuations[READABLE].iteritems():
            print '  readable fd %s' % fd, '=>', cont.__name__
        for fd, cont in self.continuations[WRITABLE].iteritems():
            print '  writable fd %s' % fd, '=>', cont.__name__

theReactor = Reactor()
theCache = {}

def runServer(port=PORT):
    downSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    downSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    downSocket.bind(('', port))
    downSocket.listen(5)
    print ts(), 'listening on', port
    
    def spawnHandler():
        handler = RequestHandler()
        handler.accept(downSocket)
        theReactor.on(downSocket, READABLE, spawnHandler)
    
    theReactor.on(downSocket, READABLE, spawnHandler)
    try:
        theReactor.run()
    except KeyboardInterrupt:
        pass
    downSocket.close()
    print ts(), "server shutting down"
        
runServer()

