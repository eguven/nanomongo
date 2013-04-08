import unittest

from nanomongo.field import Field
from nanomongo.document import BaseDocument
from nanomongo.util import (
    DotNotationMixin, valid_field, valid_client, RecordingDict,
)

try:
    import pymongo
    PYMONGO_CLIENT = pymongo.MongoClient()
except:
    PYMONGO_CLIENT = False

try:
    import motor
    MOTOR_CLIENT = motor.MotorClient().open_sync()
    # from .motor_base import async_test_engine, AssertEqual
except:
    MOTOR_CLIENT = None


class HelperFuncionsTestCase(unittest.TestCase):
    def test_invalid_clients(self):
        invalid_clients = ['foo', 42, dict(), list(), object(), tuple()]
        [self.assertFalse(valid_client(client)) for client in invalid_clients]

    @unittest.skipUnless(PYMONGO_CLIENT, 'pymongo not installed or connection refused')
    def test_valid_client_pymongo(self):
        client = pymongo.MongoClient()
        self.assertTrue(valid_client(client))

    @unittest.skipUnless(MOTOR_CLIENT, 'motor not installed or connection refused')
    def test_valid_client_motor(self):
        self.assertTrue(valid_client(MOTOR_CLIENT))


class RecordingDictTestCase(unittest.TestCase):
    def test_recording_dict(self):
        """Test `__setitem__`, `__delitem__` functionality"""
        class Doc(RecordingDict):
            pass

        d = Doc()
        nanodiff_base = {'$set': {}, '$unset': {}}
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d.foo = 42
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d['foo'] = 42
        self.assertEqual({'$set': {'foo': 42}, '$unset': {}}, d.__nanodiff__)
        d['foo'] = 1337
        self.assertEqual({'$set': {'foo': 1337}, '$unset': {}}, d.__nanodiff__)
        d.reset_diff()
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        d = Doc(foo=42)
        self.assertEqual(nanodiff_base, d.__nanodiff__)
        self.assertEqual(42, d['foo'])
        del d['foo']
        self.assertEqual({'$set': {}, '$unset': {'foo': 1}}, d.__nanodiff__)


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
