import datetime
import math
import unittest

from nanomongo import Field
from nanomongo.errors import ValidationError

def wrap(*args, **kwargs):  # to wrap Field() declarations
    def wrapper():
        Field(*args, **kwargs)
    return wrapper

class FieldTestCase(unittest.TestCase):

    def test_bad_types(self):
        """Test Field definitions with invalid types"""
        class RandomClass(object): pass
        class TypeSubclass(type): pass

        self.assertRaises(AssertionError, Field, *(RandomClass,))
        self.assertRaises(AssertionError, Field, *(TypeSubclass,))

    def test_good_types(self):
        """Test Field definitions with valid types"""
        types = (bool, int, float, bytes, str, list, dict, datetime.datetime)
        [Field(t) for t in types]

    def test_bool_field_defs(self):
        """Test Field definitions: bool"""
        valid_defs = [wrap(bool), wrap(bool, default=True), wrap(bool, default=False),
                      wrap(bool, none_ok=True), wrap(bool, none_ok=False),
                      wrap(bool, default=None, none_ok=True),
                     ]
        invalid_defs = [wrap(bool, default=1), wrap(bool, none_ok='not-bool'),
                        wrap(bool, none_ok=1), wrap(bool, max_length=1),
                        wrap(bool, empty_ok=True)
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_numeric_field_defs(self):
        """Test Field definitions: int, float"""
        # checking if defaults fit types, valid kwargs and their input
        # none_ok=True|False allowed for numeric types where empty_ok is not

        valid_defs = [wrap(int, default=42), wrap(int, default=int(math.pow(1337, 42))),
                      wrap(float, default=3.14159265), wrap(int, none_ok=True),
                     ]
        invalid_defs = [wrap(float, default=42), wrap(int, empty_ok='not-bool'),
                        wrap(float, empty_ok=True), wrap(int, none_ok='not-bool'),
                        wrap(float, max_length='not-numeric'), wrap(int, max_length=42),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_datetime_field_defs(self):
        """Test Field definitions: datetime.datetime"""
        dt = datetime.datetime
        valid_defs = [wrap(dt), wrap(dt, none_ok=True), wrap(dt, none_ok=False),
                      wrap(dt, default=dt.utcnow), wrap(dt, default=dt.utcnow()),
                     ]
        invalid_defs = [wrap(dt, none_ok='not-bool'), wrap(dt, empty_ok=True), wrap(dt, empty_ok=1),
                        wrap(dt, default=1337), wrap(dt, max_length=0),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_container_field_defs_str(self):
        """Test Field definitions: str"""
        valid_defs = [wrap(str), wrap(str, none_ok=True), wrap(str, empty_ok=True, none_ok=True),
                      wrap(str, none_ok=True, default=None), wrap(str, default='', empty_ok=True),
                      wrap(str, max_length=16), wrap(str, default='42', max_length=2),
                      wrap(str, default='', max_length=16, empty_ok=True, none_ok=True),
                     ]
        invalid_defs = [wrap(str, default=42), wrap(str, default=''), wrap(str, default=None),
                        wrap(str, default='', empty_ok=False), wrap(str, default=''.encode('utf-8')),
                        wrap(str, default='L33t', max_length=2),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_container_field_defs_bytes(self):
        """Test Field definitions: bytes"""
        valid_defs = [wrap(bytes), wrap(bytes, default=None, none_ok=True),
                      wrap(bytes, default=b'', empty_ok=True), wrap(bytes, default=b'42', max_length=2),
                     ]
        invalid_defs = [wrap(bytes, default=1), wrap(bytes, default=b'', empty_ok=False),
                        wrap(bytes, default=None, none_ok=False), wrap(bytes, default='L33t'),
                        wrap(bytes, default=None, empty_ok=False, none_ok=False),
                        wrap(bytes, default=b'L33t', max_length=2),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_container_field_defs_list(self):
        """Test Field definitions: list"""
        valid_defs = [wrap(list), wrap(list, default=[], empty_ok=True),
                      wrap(list, default=None, none_ok=True), wrap(list, default=[42, 'L33t']), 
                      wrap(list, default=[3.14159265], max_length=1),
                     ]
        invalid_defs = [wrap(list, default=1), wrap(list, default=(1,)), wrap(list, default=[]),
                        wrap(list, default=None), wrap(list, default=[], empty_ok=False),
                        wrap(list, default=None, none_ok=False),
                        wrap(list, default=[1,2,3,4], max_length=2)
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

    def test_container_field_defs_dict(self):
        """Test Field definitions: dict"""
        valid_defs = [wrap(dict), wrap(dict, default={}, empty_ok=True),
                      wrap(dict, default=None, none_ok=True), wrap(dict, default=dict(a=1)),
                      wrap(dict, default={'L33t':42}, max_length=1),
                     ]
        invalid_defs = [wrap(dict, default=[]), wrap(dict, default=''), wrap(dict, default={}),
                        wrap(dict, default=None), wrap(dict, default=dict(), empty_ok=False),
                        wrap(dict, default=None, none_ok=False),
                        wrap(dict, default=dict(key1=1, key2=2), max_length=1),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

