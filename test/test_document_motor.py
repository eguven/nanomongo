import os
import unittest

import bson
import pymongo
import six
import tornado.testing

from nanomongo.field import Field
from nanomongo.document import BaseDocument

from . import PYMONGO_CLIENT, TEST_DBNAME

try:
    import motor
    MOTOR_CLIENT = motor.MotorClient()
except ImportError:
    MOTOR_CLIENT = None

SKIP_MOTOR = bool(os.environ.get('NANOMONGO_SKIP_MOTOR'))


class MotorDocumentTestCase(tornado.testing.AsyncTestCase):

    def setUp(self):
        self.io_loop = tornado.ioloop.IOLoop.current()
        PYMONGO_CLIENT.drop_database(TEST_DBNAME)

    @unittest.skipUnless(MOTOR_CLIENT, 'motor not installed or connection refused')
    @unittest.skipIf(SKIP_MOTOR, 'NANOMONGO_SKIP_MOTOR is set')
    @tornado.testing.gen_test
    def test_insert_find_motor(self):
        """Motor: Test document save, find, find_one"""

        MOTOR_CLIENT = motor.MotorClient(io_loop=self.io_loop)

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(int, required=False)
        Doc.register(client=MOTOR_CLIENT, db=TEST_DBNAME)

        col = Doc.get_collection()
        self.assertTrue(isinstance(col, motor.MotorCollection))
        result = yield motor.Op(Doc.find_one)
        self.assertEqual(None, result)
        d = Doc(foo=six.u('foo value'), bar=42)
        _id = yield motor.Op(d.insert)
        self.assertTrue(isinstance(_id, bson.ObjectId))
        result = yield motor.Op(Doc.find({'foo': 'foo value'}).count)
        self.assertEqual(1, result)
        result = yield motor.Op(Doc.find_one, {'bar': 42})
        self.assertEqual(d, result)

    @unittest.skipUnless(MOTOR_CLIENT, 'motor not installed or connection refused')
    @unittest.skipIf(SKIP_MOTOR, 'NANOMONGO_SKIP_MOTOR is set')
    @tornado.testing.gen_test
    def test_partial_update(self):
        """Motor: partial atomic update with save"""

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(int, required=False)
            moo = Field(list)

        Doc.register(client=MOTOR_CLIENT, db=TEST_DBNAME)

        d = Doc(foo=six.u('foo value'), bar=42)
        d.moo = []
        yield motor.Op(d.insert)
        del d.bar  # unset
        yield motor.Op(d.save)
        result = yield motor.Op(Doc.find_one, {'_id': d._id})
        self.assertEqual(d, result)
        d.foo = six.u('new foo')
        d['bar'] = 1337
        d.moo = ['moo 0']
        yield motor.Op(d.save, atomic=True)
        result = yield motor.Op(Doc.find_one, {'foo': six.u('new foo'), 'bar': 1337})
        self.assertEqual(d, result)
        d.moo = []
        del d['bar']
        yield motor.Op(d.save)
        result = yield motor.Op(Doc.find_one, {'_id': d._id})
        self.assertEqual(d, result)

    @unittest.skipUnless(MOTOR_CLIENT, 'motor not installed or connection refused')
    @unittest.skipIf(SKIP_MOTOR, 'NANOMONGO_SKIP_MOTOR is set')
    @tornado.testing.gen_test
    def test_index_motor(self):
        """Motor: test index build using motor"""

        class Doc(BaseDocument):
            foo = Field(six.text_type)
            __indexes__ = [pymongo.IndexModel('foo')]

        Doc.register(client=MOTOR_CLIENT, db=TEST_DBNAME)
        # bit of a workaround, checking the current_op on the database because
        # register runs ensure_index async and returns; we end up checking Index
        # before it finishes building on slow systems (travis-ci holla!)
        op = yield motor.Op(Doc.get_collection().database.current_op)
        while op['inprog']:
            yield tornado.gen.Task(self.io_loop.call_later, 0.1)
            op = yield motor.Op(Doc.get_collection().database.current_op)
        indexes = yield motor.Op(Doc.get_collection().index_information)
        self.assertEqual(2, len(indexes))  # 1 + _id
        self.assertFalse(hasattr(Doc, '__indexes__'))
