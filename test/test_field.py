import copy
import datetime
import math
import unittest

import six

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
        types = copy.copy(Field.allowed_types)
        [Field(t) for t in types]

    def test_field_def_arguments(self):
        """Test Field definition arguments"""
        valid_defs = [
            wrap(bool, required=True), wrap(bool, required=False),
            wrap(bool, default=True), wrap(bool, default=False),
            wrap(six.binary_type, default=b'L33t'), wrap(six.text_type, default=six.u('L33t')),
            wrap(list, default=[]), wrap(six.text_type, default=None, required=False),
            wrap(datetime.datetime, auto_update=True),
            wrap(DBRef, document_class='L33tClass'),
        ]
        invalid_defs = [
            wrap(), wrap(bool, default=1), wrap(dict, default=None),
            wrap(six.text_type, required=1), wrap(six.binary_type, default=six.u('')),
            wrap(six.text_type, default=b'', required=False),
            wrap(six.text_type, default='', bad_kwarg=True), wrap(int, auto_update=True),
            wrap(datetime.datetime, auto_update='bad value'),
            wrap(DBRef, document_class=dict),
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
