import os
import unittest
import remote
import remote_server
import time
from multiprocessing import Process

class TestRemote(unittest.TestCase):
    TEST_PORT = 8011

    def setUp(self):
        # Before each test: start the server.

        self.server = Process(target=remote_server.start, args=(self.TEST_PORT,))
        self.server.start()
        time.sleep(0.1) # let the server start

        # Create the remote.
        self.r = remote.Remote('127.0.0.1', self.TEST_PORT)

    def tearDown(self):
        # After each test: kill the server.
        self.server.terminate()
        self.server.join()

    def test_execution_is_really_remote(self):
        # Start the backend process, make sure it's really executing
        # the task remotely.

        @self.r.task
        def get_server_pid():
            import os
            return os.getpid()

        self.assertNotEqual(get_server_pid(), os.getpid())

    def test_task_list(self):
        self.assertEqual(self.r.tasks(), [])
        
        @self.r.task
        def add(a, b):
            return a + b

        @self.r.task
        def multiply(a, b):
            return a * b

        # Are all the registered tasks on the list?
        self.assertEqual(sorted(self.r.tasks()),
                         [('add', 0),
                          ('multiply', 0)])

        # Check execution counters.
        add(1, 2)
        self.assertEqual(sorted(self.r.tasks()),
                         [('add', 1),
                          ('multiply', 0)])

        multiply(2, 3)
        self.assertEqual(sorted(self.r.tasks()),
                         [('add', 1),
                          ('multiply', 1)])

        multiply(2, 3)
        self.assertEqual(sorted(self.r.tasks()),
                         [('add', 1),
                          ('multiply', 2)])
                          
    def test_passing_args_and_kwargs(self):
      
      @self.r.task
      def func(ala, bob, *args, **kwargs):
        return (ala, bob, args, kwargs)
        
      self.assertEqual(func(1, 2, 3, a=4), [1, 2, [3], {'a': 4}])

    def test_return_values(self):

      @self.r.task
      def add(a, b):
        return a + b

      @self.r.task
      def divide(a, b):
        return a / b

      self.assertEqual(add(1234, 4321), 5555)
      self.assertEqual(divide(130, 10), 13)
      self.assertEqual(add(divide(10, 2), 2), 7)

if __name__ == '__main__':
    unittest.main()
