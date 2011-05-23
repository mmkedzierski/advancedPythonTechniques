#!/usr/bin/env python
# (c) mk248269
import unittest
from subprocess import Popen, PIPE, STDOUT

class TestTweaker(unittest.TestCase):

  def runAndReturnOutput(self, cmd):
    process = Popen(cmd, stdout = PIPE, stderr = STDOUT)
    process.wait()
    stdout, _ = process.communicate()
    return stdout

  def testUsageHelp(self):
    output_expected = 'Usage: ./tweaker.py <module> <tester_module>\n'
    self.assertEquals(output_expected, self.runAndReturnOutput(['./tweaker.py']))

  def testProblems(self):
    output_expected = ''.join([
      "mod1.py:4: The set of errors has changed after switching condition in 'if' statement per mod_tests1.py\n",
      "mod1.py:15: After switching condition in 'while' statement the tests have not finished their execution in mod_tests1.py\n",
      "mod1.py:17: Condition in 'if' statement irrelevant per mod_tests1.py\n",
      "mod1.py:19: Condition in 'while' statement irrelevant per mod_tests1.py\n",
      "\n",
      "4 problems found :(\n"
    ])
    self.assertEquals(output_expected, self.runAndReturnOutput(['./tweaker.py', 'mod1.py', 'mod_tests1.py']))

  def testOK(self):
    output_expected = "All OK, no problems detected\n"
    self.assertEquals(output_expected, self.runAndReturnOutput(['./tweaker.py', 'mod2.py', 'mod_tests2.py']))
if __name__ == '__main__':
  unittest.main()
