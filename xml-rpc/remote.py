import xmlrpclib
from functools import wraps
import marshal


class Remote(object):
  def __init__(self, host, port):
    self.url = "http://" + host + ":" + str(port) + "/"
    self.shots = dict()      # mapowanie: nazwa_funkcji -> liczba wywolan
    
  def encode_func(self, func):
    return (func.func_code, func.func_defaults, func.func_doc, func.func_name)
    
  def task(self, func):
    @wraps(func)
    def newfunc(*args, **kwargs):
      proxy = xmlrpclib.ServerProxy(self.url)
      self.shots[func.__name__] += 1
      return proxy.run_function(func.__name__, args, kwargs)
    proxy = xmlrpclib.ServerProxy(self.url)
    binary_repr = marshal.dumps(self.encode_func(func))
    proxy.register_function(xmlrpclib.Binary(binary_repr))
    self.shots[func.__name__] = 0
    return newfunc

  def tasks(self):
    proxy = xmlrpclib.ServerProxy(self.url, allow_none = True)
    retval = []
    for k, v in self.shots.iteritems():
      retval.append((k, v))
    return retval
