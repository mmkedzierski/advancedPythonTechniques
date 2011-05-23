import xmlrpclib
import marshal
from SimpleXMLRPCServer import SimpleXMLRPCServer
import types


functions = dict()  # mapowanie: nazwa_funkcji -> funkcja

def register_function(binary_repr):
  func = decode_func(marshal.loads(binary_repr.data))
  functions[func.__name__] = func
  
def run_function(func_name, args, kwargs):
  assert(functions.has_key(func_name))
  return functions[func_name](*args, **kwargs)
  
def decode_func(encoded):
  code, defaults, doc, name = encoded
  func = types.FunctionType(code, dict(globals()), name, defaults)
  func.__doc__ = func.func_doc = doc
  return func
  
def start(port):
  server = SimpleXMLRPCServer(("localhost", port), allow_none=True)
  server.register_function(register_function, "register_function")
  server.register_function(run_function, "run_function")
  server.serve_forever()
