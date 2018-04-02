import copy
import datetime
import types
import unittest
import sys

import six

from nanomongo.field import Field
from nanomongo.document import BaseDocument
from nanomongo.errors import *

try:
    import pymongo
    import bson
    pymongo.MongoClient()
    PYMONGO_OK = True
except:
    PYMONGO_OK = False


class DocumentTestCase(unittest.TestCase):
    def test_document_bad_field(self):
        """Test document definition with bad Field def"""

        def bad_field():
            class Doc(BaseDocument):
                foo = Field()

        def bad_field_default():
            class Doc(BaseDocument):
                foo = Field(six.text_type, default=1)

        def bad_field_name():
            class Doc(BaseDocument):
                nanomongo = Field(int)

        for func in (bad_field, bad_field_default, bad_field_name):
            self.assertRaises(TypeError, func)

    def test_document_bad_init(self):
        """Test incorrect document init"""

        class Doc(BaseDocument):
            pass
        self.assertRaises(TypeError, Doc, *(1,))
        self.assertRaises(ExtraFieldError, Doc, *({'foo': 'bar'},))
        self.assertRaises(ExtraFieldError, Doc, **{'foo': 'bar'})

        class NewDoc(Doc):
            foo = Field(dict)
        self.assertRaises(ValidationError, NewDoc, *({'foo': {'$bar': 42}},))
        self.assertRaises(ValidationError, NewDoc, **{'foo': {'bar.foo': 42}})

    def test_dot_notation_no_conflict(self):
        """Test that :class:`~nanomongo.util.DotNotationMixin` does not
        interfere when attribute access on a non-field name is UnsupportedOperation
        """
        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)

        d = Doc()
        self.assertFalse(hasattr(Doc, 'dot_notation') or hasattr(d, 'dot_notation'))
        self.assertRaises(AttributeError, lambda: d.foo)
        d.foo = 42
        self.assertTrue('foo' in d)
        # attribute set/get works as usual for names that are not fields
        self.assertRaises(AttributeError, lambda: d.bar)
        d.bar = 'bar value'
        self.assertTrue('bar' not in d)  # not in the data that we'll save
        self.assertEqual('bar value', d.bar)
        del d.bar
        self.assertRaises(AttributeError, lambda: d.bar)
        del d['foo']

        def f():
            del d.foo
        self.assertRaises(AttributeError, f)

    def test_document(self):
        """Test document definition, initialization, setting and getting
        attributes, validation
        """

        class Doc(BaseDocument):
            # dot_notation = False
            bool_a, bool_b = Field(bool), Field(bool)
            foo = Field(int, default=42)
            bar = Field(six.text_type, default=None, required=False)

        class Doc2(Doc):
            dot_notation = True
            foo = Field(dict)
            zoo = Field(list)

        d = Doc(bool_a=True)
        self.assertEqual(d, {'bool_a': True, 'foo': 42, 'bar': None})
        # bool_b not set and required
        self.assertRaises(ValidationError, d.validate_all)
        # dot_notation not active
        d.bool_b = False
        self.assertRaises(ValidationError, d.validate_all)
        d['bool_b'] = True
        d.validate_all()
        # Doc2 has field 'foo' chaged to type dict, can't create new Doc2 from Doc
        self.assertRaises(ValidationError, Doc2, *(d,))
        self.assertRaises(ValidationError, Doc2, **d)
        # this type change will allow Doc2 cast, but fail Doc validation
        d['foo'] = {'L33t': 42}
        self.assertRaises(ValidationError, d.validate_all)
        dd = Doc2(d)
        self.assertTrue(dd == Doc2(**d) ==
                        Doc2(bool_a=True, bool_b=True, foo={'L33t': 42}, bar=None))
        # dd (Doc2) still has required field 'zoo' unset
        self.assertRaises(ValidationError, dd.validate_all)
        # dd has dot_notation
        dd.zoo = [3.14159265]
        dd.validate_all()
        dd.undefined = 'undefined field value'
        dd.validate_all()  # passes because undefined Fields bypass __setattr__
        dd['undefined'] = 'undefined field value'
        self.assertRaises(ValidationError, dd.validate_all)

    def test_document_dir(self):
        """Test __dir__ functionality"""
        class Doc(BaseDocument):
            foo = Field(six.text_type)

        class Doc2(Doc):
            bar = Field(six.text_type, required=False)

        dir_base = BaseDocument()
        dir_doc = Doc()
        dir_doc2 = Doc2()
        base_dir = dir(dir_base)
        doc_dir = sorted(dir(dir_base) + Doc.nanomongo.list_fields())
        doc2_dir = sorted(doc_dir + ['bar'])


class ClientTestCase(unittest.TestCase):
    def test_document_cient_bad(self):
        def bad_client():
            class Doc(BaseDocument):
                client = ''

        def bad_db():
            class Doc(BaseDocument):
                db = 1234

        def bad_col():
            class Doc(BaseDocument):
                dot_notation = True
                collection = 3.14159265

        def db_before_client():
            class Doc(BaseDocument):
                db = 'nanomongotest'

        [self.assertRaises(TypeError, func) for func in (bad_client, bad_db, bad_col)]
        self.assertRaises(ConfigurationError, db_before_client)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_client(self):
        """Pymongo: Test correct client input and document configuration"""
        mclient = pymongo.MongoClient()

        class Doc(BaseDocument):
            client = mclient
            db = 'nanomongotest'
            dot_notation = True
            foo = Field(six.text_type)

        class Doc2(Doc):
            client = mclient
            db = 'nanomongotest'
            collection = 'othercollection'
            dot_notation = True
            bar = Field(int)

        class Doc3(Doc):
            bar = Field(float)

        d = Doc()
        dd = Doc2()
        ddd = Doc3()
        self.assertEqual(d.nanomongo.client, dd.nanomongo.client)
        self.assertEqual(mclient['nanomongotest'], d.nanomongo.database)
        self.assertEqual(mclient['nanomongotest'], dd.nanomongo.database)
        self.assertEqual('doc', d.nanomongo.collection)
        self.assertEqual('othercollection', dd.nanomongo.collection)
        self.assertNotEqual(d.nanomongo.client, ddd.nanomongo.client)
        self.assertFalse(hasattr(dd, 'client') or hasattr(dd, 'db') or
                         hasattr(dd, 'collection'))

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_configuration(self):
        """Pymongo: Test document misconfiguration eg. client, db, collection"""
        mclient = pymongo.MongoClient()

        class Doc(BaseDocument):
            pass

        class Doc2(BaseDocument):
            client = mclient

        class Doc3(BaseDocument):  # autoset
            client = mclient
            db = 'nanotestdb'

        self.assertRaises(ConfigurationError, Doc.get_collection)
        self.assertRaises(ConfigurationError, Doc2.get_collection)
        Doc3.get_collection()
        Doc3.nanomongo.collection = ''
        self.assertRaises(ConfigurationError, Doc3.get_collection)
        # register
        self.assertRaises(ConfigurationError, Doc.register)
        self.assertRaises(ConfigurationError, Doc.register, **{'client': mclient})
        self.assertRaises(TypeError, Doc.register,
                          **{'client': mclient, 'db': mclient['nanotestdb']})
        self.assertFalse(Doc.nanomongo.registered)
        Doc.register(client=mclient, db='nanotestdb')
        self.assertTrue(Doc.nanomongo.registered)
        self.assertRaises(ConfigurationError, Doc.register,
                          **{'client': mclient, 'db': 'nanotestdb'})
        m_count = len(Doc.get_collection().database.outgoing_copying_manipulators)
        self.assertEqual(1, m_count)

        Doc2.register(client=mclient, db='nanotestdb', collection='doc2_collection')


class MongoDocumentTestCase(unittest.TestCase):
    def setUp(self):
        pymongo.MongoClient().drop_database('nanotestdb')

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_insert_find(self):
        """Pymongo: Test document insert, find, find_one"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(int, required=False)
        Doc.register(client=client, db='nanotestdb')

        self.assertEqual(None, Doc.find_one())
        d = Doc(foo=six.u('foo value'))
        d.bar = 'wrong type'
        self.assertRaises(ValidationError, d.insert)
        d.bar = 42
        self.assertTrue(d.insert())
        self.assertEqual(0, Doc.find({'foo': 'inexistent'}).count())
        self.assertEqual(1, Doc.find({'foo': 'foo value'}).count())
        self.assertEqual(d, Doc.find_one())

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_partial_update(self):
        """Pymongo: Test partial atomic update with save"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(int, required=False)
            moo = Field(list)
        Doc.register(client=client, db='nanotestdb')

        d = Doc(foo=six.u('foo value'), bar=42)
        self.assertRaises(ValidationError, d.save)  # no _id yet
        d['_id'] = bson.objectid.ObjectId()
        self.assertRaises(ValidationError, d.save)  # _id manually set
        self.assertRaises(ValidationError, d.insert)  # missing field moo
        d.moo = []
        self.assertEqual(d._id, d.insert())
        del d.bar  # unset
        d.save()
        self.assertEqual(d, Doc.find_one(d._id))
        d.foo = six.u('new foo')
        d['bar'] = 1337
        d.moo = ['moo 0']
        d.save()
        self.assertEqual(d, Doc.find_one(d._id))
        d.moo = []
        del d['bar']
        d.save()
        self.assertEqual(d, Doc.find_one(d._id))
        d['extra_field'] = 'fail'
        self.assertRaises(ValidationError, d.save)
        del d['extra_field']
        d.save()
        d.bar = 'wrong type'
        self.assertRaises(ValidationError, d.save)
        self.assertRaises(ValidationError, d.insert)
        del d.bar
        d.save()
        del d.foo
        self.assertRaises(ValidationError, d.save)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_partial_update_addToSet(self):
        """Pymongo: addToSet functionality with `save`"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(list)
            bar = Field(dict)
            moo = Field(six.text_type)
        Doc.register(client=client, db='nanotestdb')

        self.assertRaises(ValidationError, Doc().addToSet, *('$fail', 42))
        self.assertRaises(ValidationError, Doc().addToSet, *('bar.$1', 42))
        # use dict.__setitem__ to bypass RecordingDict cast at self.__setitem__
        d = Doc()
        dict.__setitem__(d, 'bar', {})
        self.assertEqual(dict, type(d.bar))  # not RecordingDict
        self.assertRaises(ValidationError, d.addToSet, *('bar.1', 42))
        d = Doc(foo=['foo_1', 'foo_2'], bar={'1': 'bar_1', '2': []}, moo=six.u('moo val'))
        d.insert()
        self.assertRaises(ValidationError, d.addToSet, *('moo', 42))
        self.assertRaises(ValidationError, d.addToSet, *('moo.not_dict', 42))
        self.assertRaises(ValidationError, d.addToSet, *('undefined.field', 42))
        self.assertRaises(UnsupportedOperation, d.addToSet, *('bar.a.b', 42))
        d.addToSet('foo', 'foo_1')
        d.moo = six.u('new moo')
        d.addToSet('foo', 'foo_3')
        d.addToSet('foo', 'foo_1')
        d.addToSet('bar.2', 'L33t')
        d.addToSet('bar.3', 'new_1')
        d.addToSet('bar.3', 'new_1')
        d.addToSet('bar.3', 'new_2')
        self.assertRaises(ValidationError, d.addToSet, *('bar.1', 1))
        topdiff = {'$set': {'moo': 'new moo'}, '$unset': {},
                   '$addToSet': {'foo': {'$each': ['foo_1', 'foo_3']}}}
        subdiff = {'$set': {}, '$unset': {},
                   '$addToSet': {'2': {'$each': ['L33t']},
                                 '3': {'$each': ['new_1', 'new_2']}}}
        self.assertEqual(topdiff, d.__nanodiff__)
        self.assertEqual(subdiff, d.bar.__nanodiff__)
        d_copy = copy.deepcopy(d)
        d.save()
        d_db = Doc.find_one()
        self.assertTrue(d_copy == d == d_db)
        # check against field duplication at addToSet
        d = Doc()
        d.foo = [42]  # set -- top-level $addToSet will clash
        self.assertEqual([42], d.__nanodiff__['$set']['foo'])
        self.assertRaises(ValidationError, d.addToSet, *('foo', 42))
        del d.foo  # unset -- top-level $addToSet will clash
        self.assertRaises(ValidationError, d.addToSet, *('foo', 42))
        d = Doc(bar={})
        d.bar['1'] = [42]  # deep-level set -- dotted $addToSet will clash
        self.assertRaises(ValidationError, d.addToSet, *('bar.1', 42))
        d = Doc()
        d.bar = {'1': [42]}  # dict set on top-level -- dotted $addToSet will clash
        self.assertEqual({'bar': {'1': [42]}}, d.__nanodiff__['$set'])
        self.assertRaises(ValidationError, d.addToSet, *('bar.1', 42))

        class Doc2(BaseDocument):
            dot_notation = True
            optional = Field(dict, required=False)

        Doc2.register(client=client, db='nanotestdb')
        dd = Doc2()
        dd.insert()
        # addToSet on unset field
        dd.addToSet('optional.sub', 42)
        self.assertEqual([42], dd.optional['sub'])
        self.assertEqual({'sub': {'$each': [42]}}, dd.optional.__nanodiff__['$addToSet'])
        dd.save()
        self.assertEqual(1, Doc2.find({'optional.sub': 42}).count())

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_sub_diff(self):
        """Test embedded document diff"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(dict)
        Doc.register(client=client, db='nanotestdb')

        d = Doc()
        d.foo = six.u('foo value')
        d.bar = {'sub_a': 'a', 'sub_b': 'b'}
        d.insert()
        self.assertEqual(d, Doc.find_one())
        d.foo = six.u('foo value')
        d.bar['sub_b'] = 'b'  # no change, update will return None
        self.assertEqual(None, d.save())
        d.bar = {'sub_a': 'a', 'sub_b': 'b'}
        self.assertEqual(None, d.save())
        del d.bar['sub_a']
        d.bar['sub_c'] = 'c'
        d.foo = six.u('new foo')
        d.save()
        expected = {'_id': d._id, 'foo': 'new foo',
                    'bar': {'sub_b': 'b', 'sub_c': 'c'}}
        self.assertTrue(expected == d == Doc.find_one())

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_auto_update(self):
        """Test auto_update keyword workings"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(datetime.datetime, auto_update=True)
            moo = Field(int, required=False)
        Doc.register(client=client, db='nanotestdb')

        dt = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        d = Doc(foo=six.u('foo value'), bar=dt)
        d.insert()
        self.assertTrue(datetime.timedelta(hours=1) < d.bar - dt)
        d.moo = 42
        dt_after_insert = d.bar
        d.save()
        self.assertNotEqual(d.bar, dt_after_insert)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_dbref(self):
        """Test get_dbref functionality"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            pass
        Doc.register(client=client, db='nanotestdb')

        d = Doc()
        self.assertRaises(AssertionError, d.get_dbref)
        d.insert()
        dbref = d.get_dbref()
        self.assertTrue('doc' == dbref.collection and 'nanotestdb' == dbref.database)
        dd = d.get_collection().database.dereference(dbref)
        self.assertEqual(d['_id'], dd['_id'])

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    @unittest.skipUnless(six.PY2, 'test irrelevant on PY3')
    def test_string_types(self):
        """Test text type case (as mongodb-pymongo returned string type is always unicode)"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            foo = Field(six.binary_type)
            bar = Field(six.text_type)
        Doc.register(client=client, db='nanotestdb')
        d = Doc(foo=six.binary_type('value \xc3\xbc'), bar=six.u('value \xfc'))
        d.insert()
        dd = Doc.find_one(d['_id'])
        self.assertEqual(type(d['foo']), type(dd['foo']))
        self.assertEqual(type(d['bar']), type(dd['bar']))
        self.assertEqual(dd['foo'].decode('utf-8'), dd['bar'])

    def test_dbref_getter_methods(self):
        """Test the creation and function of ``get_<field_name>_field`` methods"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            foo = Field(six.text_type)
            self = Field(bson.DBRef, required=False, document_class='Doc')
            self2 = Field(bson.DBRef, required=False, document_class='test.test_document.Doc')
            other = Field(bson.DBRef, required=False)
        Doc.register(client=client, db='nanotestdb')
        # temporarily attach Doc to module so document class import can find it
        sys.modules[__name__].Doc = Doc

        # to test DBRef document class auto discover
        # different naming so it wont clash with other Doc2 defined here
        class XDoc2(BaseDocument):
            pass
        XDoc2.register(client=client, db='nanotestdb')

        d = Doc(foo=six.text_type('1337'))
        self.assertTrue(hasattr(d, 'get_self_field'))
        self.assertTrue(isinstance(d.get_self_field, types.MethodType))
        self.assertTrue(not hasattr(d, 'get_foo_field'))
        self.assertRaises(DBRefNotSetError, d.get_self_field)
        d.insert()
        dd = XDoc2()
        dd.insert()
        d['self'], d['self2'] = d.get_dbref(), d.get_dbref()
        d['other'] = dd.get_dbref()
        d.save()
        self.assertTrue(d == d.get_self_field() == d.get_self2_field())
        self.assertEqual({'_id': dd['_id']}, d.get_other_field())  # auto discovered
        self.assertEqual(Doc, type(d.get_self_field()))
        self.assertEqual(XDoc2, type(d.get_other_field()))

        # new subclass using same collection as XDoc2 to test undecided discover
        class Doc3(BaseDocument):
            pass
        Doc3.register(client=client, db='nanotestdb', collection='xdoc2')

        self.assertRaises(UnsupportedOperation, d.get_other_field)

        # cleanup
        del sys.modules[__name__].Doc

class IndexTestCase(unittest.TestCase):
    def setUp(self):
        if PYMONGO_OK:
            pymongo.MongoClient().drop_database('nanotestdb')

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_index_definitions(self):
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            dot_notation = True
            foo = Field(six.text_type)
            bar = Field(int)
            __indexes__ = [
                pymongo.IndexModel('foo', background=True),
                pymongo.IndexModel([('bar', pymongo.ASCENDING), ('foo', pymongo.DESCENDING)],
                      unique=True),
            ]
        Doc.register(client=client, db='nanotestdb')
        self.assertEqual(3, len(Doc.get_collection().index_information()))  # 2 + _id

        # compare defines indexes vs indexes retured from the database
        defined_indexes = [index.document['key'] for index in Doc.__indexes__]
        db_indexes = [index['key'] for index in Doc.get_collection().list_indexes()]
        # MongoDB automatically adds (_id, pymondo.ASCENDING)
        _id_index = bson.SON([('_id', 1)])
        self.assertEqual(_id_index, db_indexes[0])
        db_indexes = db_indexes[1:]
        self.assertEqual(defined_indexes, db_indexes)


        class Doc2(Doc):
            __indexes__ = [
                pymongo.IndexModel('bar'),  # index test on superclass field
            ]
        Doc2.register(client=client, db='nanotestdb')
        self.assertEqual(2, len(Doc2.get_collection().index_information()))  # 1 + _id
