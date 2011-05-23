# mk248269
from functools import wraps
import time
import signal

class TimeoutException: pass

def max_call_frequency(milliseconds, onThrottle=None):
  def defaultOnThrottle(milisecondsRemaining, continuation):
    time.sleep(milisecondsRemaining / 1000.0)
    return continuation()
  if onThrottle is None: onThrottle = defaultOnThrottle

  def the_decorator(func):
    last_time = [0]
    
    @wraps(func)
    def real_func(*args, **kwargs):
      time_now = time.time()
      millisecondsRemaining = milliseconds - (time_now - last_time[0]) * 1000.0
      if (millisecondsRemaining > 0):
        def continuation(): return func(*args, **kwargs)
        retval = onThrottle(millisecondsRemaining, continuation)
        last_time[0] = time.time()
        return retval
      else:
        retval = func(*args, **kwargs)
        last_time[0] = time.time()
        return retval
        
    return real_func
  return the_decorator


def max_running_time(miliseconds, onTimeout=None):
  def defaultOnTimeout():
    raise TimeoutException
  if onTimeout is None: onTimeout = defaultOnTimeout
  def handler(*args): onTimeout()
  
  def the_decorator(func):
    call_stack = []
    
    @wraps(func)
    def real_func(*args, **kwargs):
      last_handler = signal.getsignal(signal.SIGALRM)
      signal.signal(signal.SIGALRM, handler)
      delay, _ = signal.setitimer(signal.ITIMER_REAL, miliseconds / 1000.0)
      now = time.time()
      predicted_inner = now + delay
      predicted_outer = now + miliseconds / 1000.0
      if predicted_inner < predicted_outer:
        call_stack.append((predicted_outer, last_handler))
      retval = func(*args, **kwargs)
      
      signal.alarm(0)
      if call_stack != []:
        predicted_alarm, newHandler = call_stack.pop()
        left_time = predicted_alarm - time.time()
        if left_time > 0:
          signal.signal(signal.SIGALRM, newHandler)
          signal.setitimer(signal.ITIMER_REAL, predicted_alarm - time.time())
      return retval

    return real_func
  return the_decorator
