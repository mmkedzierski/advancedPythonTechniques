# (c) mk248269
import sqlite3
import unittest
from schema import Table, DatabaseException, InacceptableFieldsException
from schema import DatabaseIntegrityException
from operator import attrgetter

class TestSchema(unittest.TestCase):
  
  def setUp(self):
    self.db_name = '/tmp/database.db'
    class Student(Table):
      db = self.db_name
      
      def passed(self):
        return self.score >= 3
        
    self.student_class = Student
    conn = sqlite3.connect(self.db_name)
    conn.execute("DROP TABLE IF EXISTS student")
    conn.execute("CREATE TABLE Student (id INTEGER PRIMARY KEY, "
      + "name TEXT NOT NULL, score REAL UNIQUE)")
    conn.close()

  def tearDown(self):
    conn = sqlite3.connect(self.db_name)
    conn.execute("DROP TABLE IF EXISTS student")
    conn.execute("DROP TABLE IF EXISTS nasty")
    conn.close()

  def test_nonexistent_records(self):
    def extract_nonexistent_record():
      self.student_class(id=3)
    self.assertRaises(DatabaseException, extract_nonexistent_record)

  def test_save_and_load(self):
    s = self.student_class(name="Jan Kowalski", score=3)
    s.name = "John"
    s.score = 1.5
    s.save()
    s.name = "John2"
    s.score = 2
    s.load()
    self.assertEquals(s.name, "John")
    self.assertEquals(s.score, 1.5)

  def test_aliases(self):
    s = self.student_class(name="Jan Kowalski", score=3)
    self.assertEquals(s.name, "Jan Kowalski")
    self.assertEquals(s.score, 3)
    self.assertTrue(s.passed())
    
    alias = self.student_class(id=s.id)
    self.assertEquals(alias.score, s.score)
    self.assertEquals(alias.name, s.name)
    self.assertEquals(alias.score, 3)
    self.assertTrue(alias.passed())

    s.score = 2
    s.save()

    self.assertEquals(s.score, 2)
    self.assertEquals(alias.score, 3)
    self.assertFalse(s.passed())

    alias.load()
    self.assertEquals(alias.score, 2)
    self.assertEquals(s.score, 2)
    self.assertFalse(alias.passed())

  def test_itervalues(self):
    student_list = [("Ala", 0.1), ("Bob", 0.2), ("Celina", 0.3), ("Dorota", 0.4)]
    n = len(student_list)
    for (nm, sc) in student_list:
      self.student_class(name=nm, score=sc)
    in_db_list = [x for x in self.student_class.itervalues()]
    in_db_list.sort(key=attrgetter('name'))
    for i in range(n):
      self.assertEquals(in_db_list[i].name, student_list[i][0])
      self.assertEquals(in_db_list[i].score, student_list[i][1])

  def test_overwrite_restricted_field(self):
    def bad_func():
      class BadClass(Table):
        def __init__(self):
          pass
    self.assertRaises(InacceptableFieldsException, bad_func)

  def test_unique_clause(self):
    s = self.student_class(name="Ala", score=3)
    def bad_func():
      s = self.student_class(name="Bob", score=3)
    self.assertRaises(DatabaseIntegrityException, bad_func)

  def test_id_overwriting(self):
    s = self.student_class(name="Jan Kowalski", score=-1.1)
    def bad_func():
      s.id = s.id + 1
    self.assertRaises(AttributeError, bad_func)

  def test_nasty_columns(self):
    conn = sqlite3.connect(self.db_name)
    conn.execute("DROP TABLE IF EXISTS nasty")
    conn.execute("CREATE TABLE nasty (id INTEGER PRIMARY KEY, itervalues TEXT)")
    conn.commit()
    conn.close()
    class Nasty(Table):
      db = self.db_name
    def bad_func():
      Nasty(itervalues="a")
    self.assertRaises(InacceptableFieldsException, bad_func)

  def test_default_clause(self):
    conn = sqlite3.connect(self.db_name)
    conn.execute("DROP TABLE IF EXISTS student")
    conn.execute("CREATE TABLE Student (id INTEGER PRIMARY KEY, "
      + "name TEXT DEFAULT noname, score REAL DEFAULT 3.14)")
    conn.commit()
    conn.close()
    
    s = self.student_class()
    self.assertEquals(s.name, 'noname')
    self.assertEquals(s.score, 3.14)
    
    s = self.student_class(name='ktos tam')
    self.assertEquals(s.name, 'ktos tam')
    self.assertEquals(s.score, 3.14)
    
    s = self.student_class(score = 2.71)
    self.assertEquals(s.name, 'noname')
    self.assertEquals(s.score, 2.71)


if __name__ == '__main__':
  unittest.main()
