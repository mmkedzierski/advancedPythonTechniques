from datetime import datetime
from datetime import timedelta
from urlparse import urlparse
import hashlib
import os
import socket
import traceback

CHUNK_SIZE = 1024
CACHE_VALIDITY = timedelta(seconds=60)
PORT = 1000 + int(hashlib.md5(os.environ['USER']).hexdigest()[:4], 16) % 64536

theCache = {}

def ts():
    return datetime.now().strftime('%Y-%m-%d:%H:%M:%S')

def md5(text):
    return hashlib.md5(text).hexdigest()

def parseDownRequest(request):
    url = urlparse(request)
    assert url.scheme == 'http'
    assert url.hostname is not None
    assert url.path is not None
    port = 80
    if url.port: port = url.port
    return url.hostname, port, url.path

def getFromCache(host, port, path):
    if (host, port, path) in theCache:
        timestamp, downResponse = theCache[(host, port, path)]
        if datetime.now() - timestamp <= CACHE_VALIDITY:
            return downResponse
    return None

def handleConnection(downConnSocket, downAddr):
  acc1 = []
  line = None
  while True:
    line = None
    yield sock, READABLE
    chunk = sock.recv(CHUNK_SIZE)
    if not chunk: break
    for ch in chunk:
      if ch == '\n':
        line = ''.join(acc1).strip()
        for x in handleLine(line): yield x
        acc1 = []
      else:
        acc1.append(ch)
  line = ''.join(acc1).strip()
  for x in handleLine(line): yield x

def handleLine(requestLine):
  if not requestLine: continue
  print ts(), '[%s:%s]' % downAddr, 'handling', repr(requestLine)
  upHost, upPort, upPath = parseDownRequest(requestLine)
  downResponse = getFromCache(upHost, upPort, upPath)
  if downResponse is None:
    print ts(), '[%s:%s]' % downAddr, \
      'connecting to %s:%s' % (upHost, upPort)
    # recvHTTPGET(upHost, upPort, upPath)
    rcvd_page = None
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      s.connect((upHost, upPort))   # nie ma yielda
      rq = 'GET ' + upPath + ' HTTP/1.0\n\n'
      # send(s, rq)
      while rq:
        yield s, WRITABLE
        sentSize = s.send(rq)     
        rq = rq[sentSize:]
      # recv(sock)
      acc2 = []
      while True:
        yield s, READABLE
        chunk = s.recv(CHUNK_SIZE)    
        if not chunk:
          rcvd_page = ''.join(acc2)
          break
        acc2.append(chunk)
    finally:
      s.close()
    downResponse = md5(rcvd_page)
    print ts(), '[%s:%s]' % downAddr, \
      'closing connection to %s:%s' % (upHost, upPort)
  theCache[(upHost, upPort, upPath)] = (datetime.now(), downResponse)
  # send(downConnSocket, downResponse + '\n')
  data = downResponse + '\n'
  while data:
    yield downConnSocket, WRITABLE
    sentSize = downConnSocket.send(data)      # YIELD
    data = data[sentSize:]

def runServer(port=PORT):
    downSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    downSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    downSocket.bind(('', port))
    downSocket.listen(0)
    print ts(), 'listening on', port
    try:
        while True:
            downConnSocket, downAddr = downSocket.accept()   # nie ma yielda
            print ts(), "accepted connection from %s:%s" % downAddr
            try:
                handleConnection(downConnSocket, downAddr)
            except:
                traceback.print_exc()
            finally:
                downConnSocket.close()
                print ts(), "closing connection from %s:%s" % downAddr
    finally:
        downSocket.close()
        print ts(), "server shutting down"

try:
    runServer()
except KeyboardInterrupt:
    pass



  #while True:
    #try:
      #handleLine.send(yield handleLine(line))
    #except (StopIteration, GeneratorExit):
      #break
