import datetime
import math
import unittest

from bson import DBRef, ObjectId

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

        self.assertRaises(TypeError, Field, *(RandomClass,))
        self.assertRaises(TypeError, Field, *(TypeSubclass,))

    def test_good_types(self):
        """Test Field definitions with valid types"""
        types = (bool, int, float, bytes, str, list, dict, datetime.datetime, DBRef, ObjectId)
        [Field(t) for t in types]

    def test_field_def_arguments(self):
        """Test Field definition arguments"""
        valid_defs = [wrap(bool, required=True), wrap(bool, required=False),
                      wrap(bool, default=True), wrap(bool, default=False),
                      wrap(str, default='L33t'), wrap(list, default=[]),
                      wrap(str, default=None, required=False),
                     ]
        invalid_defs = [wrap(), wrap(bool, default=1), wrap(dict, default=None),
                        wrap(str, required=1), wrap(bytes, default=''),
                        wrap(str, default=b'', required=False),
                       ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(TypeError, wrapped) for wrapped in invalid_defs]