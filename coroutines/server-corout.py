import select

def request_handler():
  try:
    while True:
      downConnSocket, downAddr = downSocket.accept()
      print ts(), "accepted connection from %s:%s" % downAddr
      try:
        handleConnection(downConnSocket, downAddr)
      except (GeneratorExit, StopIteration):
        pass
      except:
        traceback.print_exc()
      finally:
        downConnSocket.close()
        print ts(), "closing connection from %s:%s" % downAddr
  finally:
    downSocket.close()
    print ts(), "server shutting down"


#class RequestHandlerCoroutine:
  #def send(self):
    #pass
    
  #def close(self):
    #pass


class Reactor:
  def __init__(self):
    self.coroutines = {}  # key: (fd, WRITABLE/READABLE), value: Coroutine
    
  def run(self):
    pass


class SleepInfo:
  def __init__(self, fd, mode, callback):
    self.fd = fd
    self.mode = mode
    self.callback = callback

''' kod przepisany z malymi zmianami z PEP 342 '''
import collections

class Reactor:
  """Manage communications between coroutines"""

  running = False

  def __init__(self):
    self.coroutines = { READABLE: {}, WRITABLE: {}, NOT_BLOCKED: collections.deque() }

  def add(self, coroutine):
    """Request that a coroutine be executed"""
    self.schedule(coroutine)

  def queue_empty(self):
    q = self.coroutines
    return q[READABLE] or q[WRITABLE] or q[NOT_BLOCKED]
    
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
    func = self.queue.popleft()
    func()

  def run(self):
    result = None
    while not self.queue_empty():
      launch_blocked_coroutine()
      launch_not_blocked_coroutine()

  def schedule(self, coroutine, stack=(), mode=NOT_BLOCKED, value=None):
    def resume():
      value = coroutine.send(value)

      if isinstance(value, types.GeneratorType): # wywolanie innej coroutine
        self.schedule(value, (coroutine,stack))
      elif isinstance(value, SleepInfo):         # spanie na deskryptorze
        newmode = value.mode
        fd = value.fd
        assert mode in [READABLE, WRITABLE]
        assert fd not in self.coroutines[mode]
        self.schedule(coroutine, stack, newmode)
      elif stack:                                # zwrocenie wartosci
        self.schedule(stack[0], stack[1], NOT_BLOCKED, value)

    if mode in [READABLE, WRITABLE]:
      self.coroutines[mode][fd]
    self.queue.append(resume)
