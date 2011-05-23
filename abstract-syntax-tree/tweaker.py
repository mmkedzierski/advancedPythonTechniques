#!/usr/bin/env python
# (c) Marian Marek Kedzierski

import sys, ast, copy, unittest, imp

LIMIT_FACTOR = 10

class TweakerFinderAndLoader:
  def load_module(self, fullname):
    if fullname == self.mod_name_core:
      filename = "%s.py (tweaked)" % fullname
      tree = self.ast_module
      
      class MyVisitor(ast.NodeVisitor):
        def visit_If(self, node):
          print node.test, node.lineno
        def visit_While(self, node):
          print node.test, node.lineno
    else:
      filename = fullname + '.py'
      assert(fullname == self.tester_name_core)
      tree = self.tester_ast_module
      
    mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
    mod.__file__ = filename
    mod.__loader__ = self
    code = compile(tree, filename, 'exec')
    exec code in mod.__dict__
    return mod

  def __init__(self, mod_name_core, tester_name_core):
    self.mod_name_core = mod_name_core
    self.tester_name_core = tester_name_core
    self.ast_module = ast.parse(self.load_text_code(mod_name_core), mod_name_core + ".py")
    self.tester_ast_module = ast.parse(self.load_text_code(tester_name_core), tester_name_core + ".py")
      
  def load_text_code(self, name_core):
    try:
      f = open(name_core + '.py')
      retval = f.read()
    finally:
      f.close()
    return retval

  def find_module(self, fullname, path=None):
    if fullname in [self.mod_name_core, self.tester_name_core]:
      return self
    return None

class LineLimiter(object):
  class LineCountExceeded: pass

  def __init__(self, limit):
    self.lineno = 0
    self.limit = limit
    self.raised = False

  def get_tracer(self):
    def tracer(frame, event, arg):
      if event == 'call':
        return tracer
      elif event == 'line':
        self.lineno += 1
        if (self.lineno > self.limit):
          self.raised = True
          #print self.lineno, ' > ', self.limit
          raise LineLimiter.LineCountExceeded
    return tracer

class LineCounter(object):
  def __init__(self):
    self.lines_executed = 0

  def get_tracer(self):
    def tracer(frame, event, arg):
      if event == 'call':
        return tracer
      elif event == 'line':
        self.lines_executed += 1
    return tracer

class ConditionSwitcher(ast.NodeVisitor):
  def __init__(self, whole_tree):
    self.conditions = []
    self.whole_tree = whole_tree
  
  def visit_If(self, node):
    self.conditions.append((node, 'if'))
  
  def visit_While(self, node):
    self.conditions.append((node, 'while'))

  def generateMutants(self):
    #print self.conditions
    for node, cond_type in self.conditions:
      old_test = node.test
      node.test = ast.copy_location(ast.UnaryOp(ast.Not(), node.test), node.test)
      new_tree = ast.fix_missing_locations(self.whole_tree)
      yield (new_tree, node.lineno, cond_type)
      node.test = old_test


class ModuleModificationManager(object):
  def __init__(self, mod_name):
    self.mod_name = mod_name
    flines = open(self.mod_name).readlines()
    flen = len(flines)
    fsource = ''.join(flines)
    self.ast_node = ast.parse(fsource)
    
  def get_initial_tester_node(self):
    return self.ast_node

  def test_case_generator(self):
    cs = ConditionSwitcher(self.ast_node)
    cs.visit(self.ast_node)
    
    for output in cs.generateMutants():
      yield output 

class TestRunner(object):
  def __init__(self, mod_name, tester_name):
    self.mod_name_core = mod_name[:-3]
    self.tester_name_core = tester_name[:-3]
    self.importer = TweakerFinderAndLoader(self.mod_name_core, self.tester_name_core)
    sys.meta_path.append(self.importer)
    
  def run_test(self, ast_module):
    self.importer.ast_module = ast_module
    try:
      del sys.modules[self.mod_name_core]
      del sys.modules[self.tester_name_core]
    except KeyError:
      pass
    tester_module = __import__(self.tester_name_core)
    testLoader = unittest.defaultTestLoader
    tests = testLoader.loadTestsFromModule(tester_module)
    resultCollector = unittest.TestResult()
    tests.run(resultCollector)
    
    return Report(resultCollector)

class Report(object):
  problems = 0
  
  def __init__(self, resultCollector):
    self.errors = [test[0]._testMethodName for test in resultCollector.errors]
    self.errors.sort()
    self.failures = [test[0]._testMethodName for test in resultCollector.failures]
    self.failures.sort()

  def testNewReport(self, other, mod_name, line, cond_type, tester_name):
    info = (mod_name, line, cond_type, tester_name)
    if other is None:
      print "%s:%d: After switching condition in '%s' statement the tests have not finished their execution in %s" % info
      Report.problems += 1
    elif self.errors != other.errors:
      print "%s:%d: The set of errors has changed after switching condition in '%s' statement per %s" % info
      Report.problems += 1
    elif self.failures == other.failures:
      print "%s:%d: Condition in '%s' statement irrelevant per %s" % info
      Report.problems += 1
     
  @classmethod
  def print_summary(cls):
    if not cls.problems:
      print "All OK, no problems detected"
    else:
      print
      print "%d problems found :(" % cls.problems
    
def main():
  if (len(sys.argv) != 3):
    print "Usage: %s <module> <tester_module>" % sys.argv[0]
    sys.exit(1)

  _, mod_name, tester_name = sys.argv

  mmm = ModuleModificationManager(mod_name)
  tr = TestRunner(mod_name, tester_name)

  # run normal test and count lines
  lc = LineCounter()
  sys.settrace(lc.get_tracer())
  original_report = tr.run_test(mmm.get_initial_tester_node())
  sys.settrace(None)
  line_limit = lc.lines_executed * LIMIT_FACTOR

  for ast_module, line, cond_type in mmm.test_case_generator():
    sys.settrace(LineLimiter(line_limit).get_tracer())
    try:
      new_report = tr.run_test(ast_module)
    except LineLimiter.LineCountExceeded:
      new_report = None
    finally:
      sys.settrace(None)
    original_report.testNewReport(new_report, mod_name, line, cond_type, tester_name)
    
  Report.print_summary()
        
main()
