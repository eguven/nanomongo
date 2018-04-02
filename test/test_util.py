import unittest

from mock import patch

from nanomongo.field import Field
from nanomongo.document import BaseDocument
from nanomongo.util import (
    DotNotationMixin, valid_field, valid_client, RecordingDict, check_keys,
    allow_client,
)
from nanomongo.errors import ValidationError

from . import PYMONGO_CLIENT, TEST_DBNAME

try:
    import motor
    MOTOR_CLIENT = motor.MotorClient()
except ImportError:
    MOTOR_CLIENT = None


class HelperFuncionsTestCase(unittest.TestCase):
    def test_invalid_clients(self):
        invalid_clients = ['foo', 42, dict(), list(), object(), tuple()]
        [self.assertFalse(valid_client(client)) for client in invalid_clients]

    @unittest.skipUnless(PYMONGO_CLIENT, 'pymongo not installed or connection refused')
    def test_valid_client_pymongo(self):
        self.assertTrue(valid_client(PYMONGO_CLIENT))

    @unittest.skipUnless(MOTOR_CLIENT, 'motor not installed or connection refused')
    def test_valid_client_motor(self):
        self.assertTrue(valid_client(MOTOR_CLIENT))

    def test_check_keys(self):
        bad_dicts = [
            {'foo.bar': 42}, {'$foo': 42}, {'foo': {'bar.foo': 42}},
            {'foo': {'$bar': 42}},
        ]
        [self.assertRaises(ValidationError, check_keys, *(dct,)) for dct in bad_dicts]
        self.assertRaises(TypeError, check_keys, *([],))

    @unittest.skipUnless(PYMONGO_CLIENT, 'pymongo not installed or connection refused')
    def test_check_spec(self):
        """Test check spec and warning messages"""
        class Doc(BaseDocument):
            foo = Field(str)
            foo_list = Field(list)
            foo_dict = Field(dict)
        Doc.register(client=PYMONGO_CLIENT, db=TEST_DBNAME)

        with patch('nanomongo.util.logging') as mock_logging:
            Doc.find({'bar': 42})  # field doesn't exist
            self.assertTrue(mock_logging.warning.called)
        with patch('nanomongo.util.logging') as mock_logging:
            Doc.find({'bar.foo': 42})  # field doesn't exist
            self.assertTrue(mock_logging.warning.called)
        with patch('nanomongo.util.logging') as mock_logging:
            Doc.find({'foo': 42})  # field type mismatch
            self.assertTrue(mock_logging.warning.called)
        with patch('nanomongo.util.logging') as mock_logging:
            Doc.find({'foo.bar': 42})  # field not dict/list
            self.assertTrue(mock_logging.warning.called)
            # OK cases
        with patch('nanomongo.util.logging') as mock_logging:
            Doc.find({'foo': '42'})
            self.assertFalse(mock_logging.warning.called)
            Doc.find({'foo_list.foo': 42})
            self.assertFalse(mock_logging.warning.called)
            Doc.find({'foo_dict.foo': 42})
            self.assertFalse(mock_logging.warning.called)

    def test_allow_mock(self):
        class MockClient():
            pass

        client = MockClient()
        self.assertFalse(valid_client(client))
        allow_client(MockClient)
        self.assertTrue(valid_client(client))


class RecordingDictTestCase(unittest.TestCase):
    def test_recording_dict(self):
        """Test `__setitem__`, `__delitem__` functionality"""
        class Doc(RecordingDict):
            pass

        d = Doc()
        nanodiff_base = {'$set': {}, '$unset': {}, '$addToSet': {}}
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d.foo = 42
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d['foo'] = 42
        self.assertEqual({'$set': {'foo': 42}, '$unset': {}, '$addToSet': {}}, d.__nanodiff__)
        d['foo'] = 1337
        self.assertEqual({'$set': {'foo': 1337}, '$unset': {}, '$addToSet': {}}, d.__nanodiff__)
        d.reset_diff()
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d = Doc(foo=42)
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        self.assertEqual(42, d['foo'])
        del d['foo']
        self.assertEqual({'$set': {}, '$unset': {'foo': 1}, '$addToSet': {}}, d.__nanodiff__)
        d['foo'] = "L33t"
        self.assertEqual({'$set': {'foo': "L33t"}, '$unset': {}, '$addToSet': {}}, d.__nanodiff__)

    def test_sub_diff(self):
        """Test functionality of sub_diff for embedded documents"""
        class Doc(RecordingDict):
            pass

        nanodiff_base = {'$set': {}, '$unset': {}, '$addToSet': {}}
        d = Doc()
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d['sub'] = Doc()
        self.assertEqual({'$set': {'sub': {}}, '$unset': {}, '$addToSet': {}}, d.__nanodiff__)
        d.reset_diff()
        d['sub']['foo'] = 42
        self.assertEqual(nanodiff_base, d.__nanodiff__)  # no diff on top level
        self.assertEqual({'$set': {'foo': 42}, '$unset': {}, '$addToSet': {}}, d['sub'].__nanodiff__)
        subdiff = d.get_sub_diff()
        self.assertEqual({'$set': {'sub.foo': 42}, '$unset': {}, '$addToSet': {}}, subdiff)
        del d['sub']['foo']
        d['sub']['bar'] = 1337
        expected = {'$set': {'sub.bar': 1337}, '$unset': {'sub.foo': 1}, '$addToSet': {}}
        self.assertEqual(expected, d.get_sub_diff())
        d.reset_diff()
        d['sub']['bar'] = 1337  # same value set
        self.assertEqual(nanodiff_base, d.get_sub_diff())


class MixinTestCase(unittest.TestCase):
    def test_mixin(self):
        """Test dot_notation mixin"""
        class Doc(BaseDocument, DotNotationMixin):
            foo = Field(str)

        d = Doc()
        self.assertTrue(valid_field(d, 'foo'))
        self.assertRaises(AttributeError, lambda: d.foo)
        d['foo'] = 'bar'
        self.assertTrue('bar' == d['foo'] == d.foo)
        d.foo = 'foobar'
        self.assertTrue('foobar' == d['foo'] == d.foo)
        self.assertRaises(AttributeError, lambda: d.undefined)
        d.undefined = 42
        self.assertEqual(42, d.undefined)
        self.assertRaises(KeyError, lambda: d['undefined'])
