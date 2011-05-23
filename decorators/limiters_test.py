# mk248269
import limiters
import time
import unittest

class TestLimiters(unittest.TestCase):
  max_call_freq_launches = 10
  
  def test_max_call_frequency(self):
    t = time.time()
    times = []
    
    @limiters.max_call_frequency(10.0)
    def func(): 
      times.append(float("%.2f" % (time.time() - t)))
      
    for i in range(self.max_call_freq_launches): func()
    expectedTimes = [round(0.01*i,2) for i in range(self.max_call_freq_launches)]
    self.assertEquals(times, expectedTimes)
    
  def test_max_running_time(self):
    @limiters.max_running_time(10)
    def long_func(): 
      time.sleep(0.02)
    def short_func(): 
      pass
    self.assertRaises(limiters.TimeoutException, long_func)
    short_func()
  
  def test_nested_max_running_time(self):
    @limiters.max_running_time(5)
    def inner_func():
      pass
    
    @limiters.max_running_time(10)
    def outer_func():
      time.sleep(0.001)
      inner_func()
      time.sleep(0.01)
      
    self.assertRaises(limiters.TimeoutException, outer_func)


if __name__ == '__main__':
  unittest.main()
