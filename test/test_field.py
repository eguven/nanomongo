import datetime
import math
import unittest

from bson import DBRef, ObjectId

from nanomongo.field import Field
from nanomongo.errors import ValidationError


def wrap(*args, **kwargs):  # to wrap Field() declarations
    def wrapper():
        Field(*args, **kwargs)
    return wrapper


class FieldTestCase(unittest.TestCase):

    def test_bad_types(self):
        """Test Field definitions with invalid types"""
        class RandomClass(object):
            pass

        class TypeSubclass(type):
            pass

        self.assertRaises(TypeError, Field, *(RandomClass,))
        self.assertRaises(TypeError, Field, *(TypeSubclass,))
        self.assertRaises(TypeError, Field, *(1,))

    def test_good_types(self):
        """Test Field definitions with valid types"""
        types = (bool, int, float, bytes, str, list, dict, datetime.datetime, DBRef, ObjectId)
        [Field(t) for t in types]

    def test_field_def_arguments(self):
        """Test Field definition arguments"""
        valid_defs = [
            wrap(bool, required=True), wrap(bool, required=False),
            wrap(bool, default=True), wrap(bool, default=False),
            wrap(str, default='L33t'), wrap(list, default=[]),
            wrap(str, default=None, required=False),
            wrap(datetime.datetime, auto_update=True),
        ]
        invalid_defs = [
            wrap(), wrap(bool, default=1), wrap(dict, default=None),
            wrap(str, required=1), wrap(bytes, default=''),
            wrap(str, default=b'', required=False),
            wrap(str, default='', bad_kwarg=True), wrap(int, auto_update=True),
            wrap(datetime.datetime, auto_update='bad value'),
        ]
        [wrapped() for wrapped in valid_defs]
        [self.assertRaises(TypeError, wrapped) for wrapped in invalid_defs]

    def test_field_validators(self):
        """Test some validators"""
        bad_dicts = [
            {'foo.bar': 42}, {'$foo': 42}, {'foo': {'bar.foo': 42}},
            {'foo': {'$bar': 42}},
        ]
        for dct in bad_dicts:
            self.assertRaises(ValidationError, Field(dict).validator, *(dct,))
