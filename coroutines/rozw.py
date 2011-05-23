# author Marian Marek Kedzierski mk248269

from datetime import datetime
from datetime import timedelta
from urlparse import urlparse
import collections
import hashlib
import os
import random
import select
import socket
import traceback


CHUNK_SIZE = 1024
CACHE_VALIDITY = timedelta(seconds=60)
PORT = 1000 + int(hashlib.md5(os.environ['USER']).hexdigest()[:4], 16) % 64536

class READABLE: pass
class WRITABLE: pass
class NOT_BLOCKED: pass

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
    yield (downConnSocket, READABLE)
    chunk = downConnSocket.recv(CHUNK_SIZE)
    if not chunk: break
    for ch in chunk:
      if ch == '\n':
        line = ''.join(acc1).strip()
        for yielded_val in handleLine(line, downConnSocket, downAddr):
          yield yielded_val
        acc1 = []
      else:
        acc1.append(ch)
  line = ''.join(acc1).strip()
  for yielded_val in handleLine(line, downConnSocket, downAddr):
    yield yielded_val

def handleLine(requestLine, downConnSocket, downAddr):
  if not requestLine: return
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
      s.connect((upHost, upPort))   
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
    sentSize = downConnSocket.send(data)
    data = data[sentSize:]


class Reactor:
  def __init__(self):
    self.coroutines = { READABLE: {}, WRITABLE: {}, NOT_BLOCKED: collections.deque() }

  def launch_blocked_coroutine(self):
    if self.coroutines[READABLE] or self.coroutines[WRITABLE]:
      readWatches = self.coroutines[READABLE].keys()
      writeWatches = self.coroutines[WRITABLE].keys()
      readables, writables, _ = select.select(readWatches, writeWatches, [])
      readables = map(lambda fd: (fd, READABLE), readables)
      writables = map(lambda fd: (fd, WRITABLE), writables)
      fd, mode = random.choice(readables + writables)
      coroutine = self.coroutines[mode][fd]
      del self.coroutines[mode][fd]
      try:
        coroutine()
      except Exception:
        traceback.print_exc()

  def launch_not_blocked_coroutine(self):
    if self.coroutines[NOT_BLOCKED]:
      func = self.coroutines[NOT_BLOCKED].popleft()
      func()

  def queue_nonempty(self):
    q = self.coroutines
    return q[READABLE] or q[WRITABLE] or q[NOT_BLOCKED]

  def run(self):
    while self.queue_nonempty():
      self.launch_blocked_coroutine()
      self.launch_not_blocked_coroutine()

  def schedule(self, coroutine, mode=NOT_BLOCKED, fd=None):
    def resume():
      try:
        retval = coroutine.next()
      except (StopIteration, GeneratorExit):
        pass
      else:
        if retval: # coroutine czeka na select()
          sock, mode = retval

          fd = sock.fileno()
          assert mode in [READABLE, WRITABLE]
          assert fd not in self.coroutines[mode]
          self.schedule(coroutine, mode, fd)
        else: 
          self.schedule(coroutine)

    if mode == NOT_BLOCKED:
      self.coroutines[mode].append(resume)
    else:
      self.coroutines[mode][fd] = resume

theReactor = Reactor()

def runServer(port=PORT):
  downSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  downSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  downSocket.bind(('', port))
  downSocket.listen(0)
  print ts(), 'listening on', port
  try:
    while True:
      yield (downSocket, READABLE)
      downConnSocket, downAddr = downSocket.accept()
      print ts(), "accepted connection from %s:%s" % downAddr
      theReactor.schedule(handleConnection(downConnSocket, downAddr))
  finally:
    downSocket.close()
    print ts(), "server shutting down"

def main():
  theReactor.schedule(runServer())
  theReactor.run()

main()
