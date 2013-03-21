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
		class RandomClass(object): pass
		class TypeSubclass(type): pass

		self.assertRaises(AssertionError, Field, *(RandomClass,))
		self.assertRaises(AssertionError, Field, *(TypeSubclass,))

	def test_good_types(self):
		types = (bool, int, float, bytes, str, list, dict, datetime.datetime)
		[Field(t) for t in types]

	def test_bool_field_defs(self):
		valid_defs = [wrap(bool), wrap(bool, default=True), wrap(bool, default=False),
					  wrap(bool, none_ok=True), wrap(bool, none_ok=False),
					 ]
		invalid_defs = [wrap(bool, default=1), wrap(bool, none_ok='not-bool'),
					    wrap(bool, none_ok=1), wrap(bool, max_length=1),
					    wrap(bool, empty_ok=True)
					   ]
		[wrapped() for wrapped in valid_defs]
		[self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

	def test_numeric_field_defs(self):
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
		dt = datetime.datetime
		valid_defs = [wrap(dt), wrap(dt, none_ok=True), wrap(dt, none_ok=False),
					  wrap(dt, default=dt.utcnow), wrap(dt, default=dt.utcnow()),
					 ]
		invalid_defs = [wrap(dt, none_ok='not-bool'), wrap(dt, empty_ok=True), wrap(dt, empty_ok=1),
						wrap(dt, default=1337), wrap(dt, max_length=0),
					   ]
		[wrapped() for wrapped in valid_defs]
		[self.assertRaises(AssertionError, wrapped) for wrapped in invalid_defs]

	def test_container_field_defs(self):
		pass








