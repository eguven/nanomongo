from __future__ import absolute_import, division
import copy
import datetime
import unittest

from nanomongo import Field
from nanomongo.errors import ValidationError

class FieldTestCase(unittest.TestCase):

	def test_bad_types(self):
		class RandomClass(object): pass
		class TypeSubclass(type): pass

		self.assertRaises(AssertionError, Field, *(RandomClass,))
		self.assertRaises(AssertionError, Field, *(TypeSubclass,))

	def test_good_types(self):
		types = (bool, int, long, float, str, unicode, list, dict, datetime.datetime)
		[Field(t) for t in types]

	def test_numeric_field_defs(self):
		# checking if defaults fit types, valid kwargs and their input
		# none_ok=True|False allowed for numeric types where empty_ok is not
		def wrap(*args, **kwargs):  # to wrap Field() declarations
			def wrapper():
				Field(*args, **kwargs)
			return wrapper
		valid_defs = [wrap(int, default=42), wrap(long, default=13371337133713371337),
					  wrap(float, default=3.14159265), wrap(int, none_ok=True),
					 ]
		invalid_defs = [wrap(int, default=13371337133713371337), wrap(float, default=42),
						wrap(long, default=42), wrap(int, empty_ok='not-bool'),
						wrap(float, empty_ok=True), wrap(long, none_ok='not-bool'),
						wrap(float, max_length='not-numeric'), wrap(long, max_length=42),
					   ]
		[wrapped() for wrapped in valid_defs]
		[self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]










