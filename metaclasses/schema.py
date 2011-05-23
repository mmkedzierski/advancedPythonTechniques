# (c) mk248269
# Zadanie 8 z bonusem
import sqlite3
import string
import random

class PrimaryKeyException(Exception): pass
class WrongSqlValue(Exception): pass
class InacceptableFieldsException(Exception): pass
class DatabaseException(Exception): pass
class DatabaseIntegrityException(DatabaseException): pass
class RecordNotFoundException(DatabaseException): pass

the_forbidden_fields = set([
  'load', '_Table__check_sql_column',
  '_Table__table_name', '_Table__do_connect',
  '_Table__update_myself', '_Table__disconnect', '_Table__new_id',
  'itervalues', '_Table__create_record', 'save', '__init__'
])

class TableMetaclass(type):
  def __new__(meta, classname, bases, classDict):
    inacceptable_fields = the_forbidden_fields.intersection(set(classDict.keys()))
    if classname != "Table" and len(inacceptable_fields) > 0:
      raise InacceptableFieldsException("Attempt to overwrite "
        + "one of the restricted fields: " + str(list(inacceptable_fields)))
    classDict['_Table__table_name'] = classname
    return type.__new__(meta, classname, bases, classDict)

class Table(object):
  __metaclass__ = TableMetaclass
  db = ':memory:'

  def __init__(self, *args, **kwargs):
    if args == (None,): return # for the needs of itervalues()
    assert args == ()
    cls = self.__class__
    cls.__do_connect()
    given_keys = kwargs.keys()
    given_keys.sort()

    if (given_keys == [cls.__id_name]):
      cur = cls.__conn.cursor()
      # select the record with the given id
      cls.__check_sql_column(cls.__table_name)
      query = cur.execute("SELECT * FROM " + cls.__table_name
        + " WHERE " + cls.__id_name + " = ?", (kwargs[cls.__id_name],))
      row = query.fetchone()
      if row is None:
        raise RecordNotFoundException("No record with "
          + cls.__id_name + " = " + str(kwargs[cls.__id_name]))
    elif (set(cls.__all_non_ids).issuperset(set(given_keys))):
      for k in set(cls.__all_non_ids).difference(set(given_keys)):
        kwargs[k] = cls.__defaults[k]
      row = cls.__create_record(kwargs)
    else:
      cls.__disconnect()
      raise ValueError
    cls.__disconnect()
    self.__update_myself(row)

  def __update_myself(self, row):
    cls = self.__class__
    for k, v in row.iteritems():
      if k in the_forbidden_fields:
        raise InacceptableFieldsException(
          "Attempt to overwrite the restricted field '" + k + "'")
      # self.<id_name> is only a descriptor;
      # the real id is held in self._Table__<id_name>
      if k == cls.__id_name:
        setattr(self, '_Table__' + k, v) 
      else:
        setattr(self, k, v)

  def save(self):
    cls = self.__class__
    cls.__do_connect()
    cls.__check_sql_column(cls.__table_name)
    sql = "UPDATE " + cls.__table_name + " SET "
    to_paste = []
    for col in cls.__all_non_ids:
      if to_paste != []: sql += ', '
      cls.__check_sql_column(col)
      sql += col + " = ?"
      if hasattr(self, col):
        to_paste.append(getattr(self, col))
      else:
        to_paste.append(None)
    cls.__check_sql_column(cls.__id_name)
    sql += " WHERE " + cls.__id_name + " = ?"
    to_paste.append(getattr(self, cls.__id_name))
    try:
      cls.__conn.execute(sql, tuple(to_paste))
    except sqlite3.IntegrityError:
      DatabaseIntegrityException("Data base integrity violated")
    cls.__conn.commit()
    cls.__disconnect()

  def load(self):
    cls = self.__class__
    cls.__do_connect()
    the_id = getattr(self, cls.__id_name)
    cls.__check_sql_column(cls.__table_name)
    cls.__check_sql_column(cls.__id_name)
    sql = "SELECT * FROM " + cls.__table_name + " WHERE " + cls.__id_name + " = ?"
    row = cls.__conn.execute(sql, (the_id,)).fetchone()
    self.__update_myself(row)
    cls.__disconnect()

  @classmethod
  def itervalues(cls):
    conn = cls.__do_connect()
    query = cls.__conn.execute("SELECT * FROM " + cls.__table_name)
    while (True):
      row = query.fetchone()
      if row is None: break
      instance = cls(None)
      instance.__update_myself(row)
      yield instance
    cls.__disconnect()
    
  @classmethod
  def __do_connect(cls):
    def dict_factory(cursor, row):
      d = {}
      for idx, col in enumerate(cursor.description):
          d[col[0]] = row[idx]
      return d
    cls.__conn = sqlite3.connect(cls.db, isolation_level=None)
    cur = cls.__conn.cursor()
    query = cur.execute("PRAGMA table_info(" + cls.__table_name + ");")
    cls.__all_non_ids = []
    columns = query.fetchall()
    primary_key_found = False
    cls.__defaults = {}
    for col in columns:
      if col[5]:
        cls.__id_name = col[1]
        cls.__id_type = str(col[2])
        primary_key_found = True
      else: cls.__all_non_ids.append(str(col[1]))
      if not col[4] is None:
        cls.__defaults[col[1]] = col[4]
    if not primary_key_found:
      raise PrimaryKeyException('no primary key in table')
    cls.__all_non_ids.sort()
    cls.__conn.row_factory = dict_factory
    
    # make self.<id_name> a read-only descriptor;
    # the real id is held in self._Table__<id_name>
    def read_only(self):
      return getattr(self, '_Table__' + cls.__id_name)
    setattr(cls, cls.__id_name, property(read_only))
    
  @classmethod
  def __disconnect(cls):
    cls.__conn.close()

  @classmethod
  def __new_id(cls):
    x = random.random() * 1000000.0
    if cls.__id_type == 'INTEGER':
      return str(int(x))
    elif cls.__id_type == 'TEXT':
      return "'" + str(x) + "'"
    elif cls.__id_type == 'REAL':
      return str(x)
    else:
      raise DatabaseException("Unsupported type: " + cls.__id_type)

  @classmethod
  def __create_record(cls, val_dict):
    # create new record
    cur = cls.__conn.cursor()
    cls.__check_sql_column(cls.__table_name)
    cls.__check_sql_column(cls.__id_name)
    new_id = cls.__new_id()
    sql = "INSERT INTO " + cls.__table_name + "(" + cls.__id_name
    to_paste = []
    for col in cls.__all_non_ids:
      sql += ', '
      cls.__check_sql_column(col)
      sql += col
    sql += ") VALUES (" + new_id
    for col in cls.__all_non_ids:
      sql += ', '
      value = str(val_dict[col])
      sql += "?"
      to_paste.append(value)
    sql += ")"
    try:
      cur.execute(sql, tuple(to_paste))
    except sqlite3.IntegrityError:
      DatabaseIntegrityException("Data base integrity violated")
    cls.__conn.commit()
    sql = "SELECT * FROM " + cls.__table_name + " WHERE " + cls.__id_name + " = ?"
    query = cur.execute(sql, (new_id,))
    retval = query.fetchone()
    if retval is None: raise DatabaseIntegrityException("Data has not been added")
    return retval

  @classmethod
  def __check_sql_column(cls, str_col):
    for s in str_col:
      if s not in string.digits + string.letters + '_':
        raise WrongSqlValue(str_col)
