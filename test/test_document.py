import copy
import datetime
import unittest

from nanomongo.field import Field
from nanomongo.document import BaseDocument, Index
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
                foo = Field(str, default=1)

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
        class Doc(BaseDocument, dot_notation=True):
            foo = Field(str)

        d = Doc()
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
            bool_a, bool_b = Field(bool), Field(bool)
            foo = Field(int, default=42)
            bar = Field(str, default=None, required=False)

        class Doc2(Doc, dot_notation=True):
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
            foo = Field(str)

        class Doc2(Doc):
            bar = Field(str, required=False)

        dir_base = BaseDocument()
        dir_doc = Doc()
        dir_doc2 = Doc2()
        base_dir = dir(dir_base)
        doc_dir = sorted(dir(dir_base) + Doc.nanomongo.list_fields())
        doc2_dir = sorted(doc_dir + ['bar'])


class ClientTestCase(unittest.TestCase):
    def test_document_cient_bad(self):
        def bad_client():
            class Doc(BaseDocument, client=''):
                pass

        def bad_db():
            class Doc(BaseDocument, db=1234):
                pass

        def bad_col():
            class Doc(BaseDocument, dot_notation=True, collection=3.14159265):
                pass

        def db_before_client():
            class Doc(BaseDocument, db='nanomongotest'):
                pass

        [self.assertRaises(TypeError, func) for func in (bad_client, bad_db, bad_col)]
        self.assertRaises(ConfigurationError, db_before_client)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_client(self):
        """Pymongo: Test correct client input and document configuration"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanomongotest'):
            foo = Field(str)

        class Doc2(Doc, dot_notation=True, client=client, db='nanomongotest',
                   collection='othercollection'):
            bar = Field(int)

        class Doc3(Doc):
            bar = Field(float)

        d = Doc()
        dd = Doc2()
        ddd = Doc3()
        self.assertEqual(d.nanomongo.client, dd.nanomongo.client)
        self.assertEqual(client['nanomongotest'], d.nanomongo.database)
        self.assertEqual(client['nanomongotest'], dd.nanomongo.database)
        self.assertEqual('doc', d.nanomongo.collection)
        self.assertEqual('othercollection', dd.nanomongo.collection)
        self.assertNotEqual(d.nanomongo.client, ddd.nanomongo.client)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_configuration(self):
        """Pymongo: Test document misconfiguration eg. client, db, collection"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument):
            pass

        class Doc2(BaseDocument, client=client):
            pass

        class Doc3(BaseDocument, client=client, db='nanotestdb'):  # autoset
            pass

        self.assertRaises(ConfigurationError, Doc.get_collection)
        self.assertRaises(ConfigurationError, Doc2.get_collection)
        Doc3.get_collection()
        Doc3.nanomongo.collection = ''
        self.assertRaises(ConfigurationError, Doc3.get_collection)
        # register
        self.assertRaises(ConfigurationError, Doc.register)
        self.assertRaises(ConfigurationError, Doc.register, **{'client': client})
        self.assertRaises(TypeError, Doc.register,
                          **{'client': client, 'db': client['nanotestdb']})
        self.assertFalse(Doc.nanomongo.registered)
        Doc.register(client=client, db='nanotestdb')
        self.assertTrue(Doc.nanomongo.registered)
        self.assertRaises(ConfigurationError, Doc.register,
                          **{'client': client, 'db': 'nanotestdb'})
        m_count = len(Doc.get_collection().database.outgoing_copying_manipulators)
        self.assertEqual(1, m_count)

        Doc2.register(client=client, db='nanotestdb', collection='doc2_collection')

class MongoDocumentTestCase(unittest.TestCase):
    def setUp(self):
        pymongo.MongoClient().drop_database('nanotestdb')

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_insert_find(self):
        """Pymongo: Test document insert, find, find_one"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(int, required=False)

        self.assertEqual(None, Doc.find_one())
        d = Doc(foo='foo value')
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

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(int, required=False)
            moo = Field(list)

        d = Doc(foo='foo value', bar=42)
        self.assertRaises(ValidationError, d.save)  # no _id yet
        d['_id'] = bson.objectid.ObjectId()
        self.assertRaises(ValidationError, d.save)  # _id manually set
        self.assertRaises(ValidationError, d.insert)  # missing field moo
        d.moo = []
        self.assertEqual(d._id, d.insert())
        del d.bar  # unset
        d.save()
        self.assertEqual(d, Doc.find_one({'_id': d._id}))
        d.foo = 'new foo'
        d['bar'] = 1337
        d.moo = ['moo 0']
        d.save(atomic=True)
        self.assertEqual(d, Doc.find_one({'_id': d._id}))
        d.moo = []
        del d['bar']
        d.save()
        self.assertEqual(d, Doc.find_one({'_id': d._id}))
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

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(list)
            bar = Field(dict)
            moo = Field(str)

        self.assertRaises(ValidationError, Doc().addToSet, *('$fail', 42))
        self.assertRaises(ValidationError, Doc().addToSet, *('bar.$1', 42))
        # use dict.__setitem__ to bypass RecordingDict cast at self.__setitem__
        d = Doc()
        dict.__setitem__(d, 'bar', {})
        self.assertEqual(dict, type(d.bar))  # not RecordingDict
        self.assertRaises(ValidationError, d.addToSet, *('bar.1', 42))
        d = Doc(foo=['foo_1', 'foo_2'], bar={'1': 'bar_1', '2': []}, moo='moo val')
        d.insert()
        self.assertRaises(ValidationError, d.addToSet, *('moo', 42))
        self.assertRaises(ValidationError, d.addToSet, *('moo.not_dict', 42))
        self.assertRaises(ValidationError, d.addToSet, *('undefined.field', 42))
        self.assertRaises(UnsupportedOperation, d.addToSet, *('bar.a.b', 42))
        d.addToSet('foo', 'foo_1')
        d.moo = 'new moo'
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

        class Doc2(BaseDocument, dot_notation=True):
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

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(dict)

        d = Doc()
        d.foo = 'foo value'
        d.bar = {'sub_a': 'a', 'sub_b': 'b'}
        d.insert()
        self.assertEqual(d, Doc.find_one())
        d.foo = 'foo value'
        d.bar['sub_b'] = 'b'  # no change, update will return None
        self.assertEqual(None, d.save())
        d.bar = {'sub_a': 'a', 'sub_b': 'b'}
        self.assertEqual(None, d.save())
        del d.bar['sub_a']
        d.bar['sub_c'] = 'c'
        d.foo = 'new foo'
        d.save()
        expected = {'_id': d._id, 'foo': 'new foo',
                    'bar': {'sub_b': 'b', 'sub_c': 'c'}}
        self.assertTrue(expected == d == Doc.find_one())

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_auto_update(self):
        """Test auto_update keyword workings"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(datetime.datetime, auto_update=True)
            moo = Field(int, required=False)

        dt = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        d = Doc(foo='foo value', bar=dt)
        d.insert()
        self.assertTrue(datetime.timedelta(hours=1) < d.bar - dt)
        d.moo = 42
        dt_after_insert = d.bar
        d.save()
        self.assertNotEqual(d.bar, dt_after_insert)


class IndexTestCase(unittest.TestCase):
    def setUp(self):
        if PYMONGO_OK:
            pymongo.MongoClient().drop_database('nanotestdb')

    def test_index_definitions_bad(self):

        self.assertRaises(TypeError, Index)

        class FooDoc(BaseDocument, dot_notation=True):
            foo = Field(str)

        def bad_def_type_1():  # no fields -> no nanomongo -> no __indexes__ allowed
            class Doc(BaseDocument):
                __indexes__ = ''

        def bad_def_type_2():  # bad __indexes__ content
            class Doc(FooDoc):
                __indexes__ = ['foo']

        def bad_def_type_3():  # bad __indexes__ content
            class Doc(FooDoc):
                __indexes__ = [Index(1)]

        def bad_def_type_4():
            class Doc(FooDoc):  # bad __indexes__ content
                __indexes__ = [Index([(1,)])]

        def def_mismatch_1():  # index field not defined
            class Doc(FooDoc):
                __indexes__ = [Index('bar')]

        def def_mismatch_2():  # list form mismatch, first position
            class Doc(FooDoc):
                __indexes__ = [Index([('bar', 1)])]

        def def_mismatch_3():  # list form mismatch, second position
            class Doc(FooDoc):
                __indexes__ = [
                    Index([('foo', pymongo.ASCENDING), ('bar', pymongo.DESCENDING)]),
                ]

        def def_mismatch_4():
            class Doc(BaseDocument):
                foo = Field(str)
                bar = Field(int)
                __indexes__ = [
                    Index('foo.fail'),
                    Index([('foo.fail', pymongo.ASCENDING), ('bar.fail', pymongo.ASCENDING)]),
                ]

        counts = {'type': 0, 'mismatch': 0}
        for fname, func in locals().items():  # run the above defined functions
            if 'type' in fname:
                counts['type'] += 1
                self.assertRaises(TypeError, func)
            elif 'mismatch' in fname:
                counts['mismatch'] += 1
                self.assertRaises(IndexMismatchError, func)
        self.assertTrue(4 == counts['type'] == counts['mismatch'])

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_index_definitions(self):
        client = pymongo.MongoClient()

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(int)
            __indexes__ = [
                Index('foo'),
                Index([('bar', pymongo.ASCENDING), ('foo', pymongo.DESCENDING)],
                      unique=True),
            ]

        self.assertEqual(3, len(Doc.get_collection().index_information()))  # 2 + _id

        class Doc2(Doc, client=client, db='nanotestdb'):
            moo = Field(float)
            __indexes__ = [
                Index('bar'),  # pointless, but index test on superclass field
                Index([('moo', pymongo.DESCENDING), ('foo', pymongo.ASCENDING)]),
            ]

        self.assertEqual(3, len(Doc2.get_collection().index_information()))  # 2 + _id

        class Doc3(BaseDocument):
            foo = Field(str)
            __indexes__ = [Index('foo')]

        self.assertTrue(hasattr(Doc3, '__indexes__'))
        Doc3.register(client=client, db='nanotestdb')
        self.assertEqual(2, len(Doc3.get_collection().index_information()))  # 1 + _id
        self.assertFalse(hasattr(Doc3, '__indexes__'))

        class Doc4(BaseDocument):
            # test indexes on dotted keys
            foo = Field(list)
            bar = Field(dict)
            __indexes__ = [
                Index('bar.moo'),
                # compund on two embedded document fields
                Index([('bar.moo', pymongo.ASCENDING), ('bar.zoo', pymongo.ASCENDING)]),
                # compound on embedded document field + list element document field
                Index([('bar.moo', pymongo.ASCENDING), ('foo.whatever', pymongo.ASCENDING)]),
            ]

        Doc4.register(client=client, db='nanotestdb')
        self.assertEqual(4, len(Doc4.get_collection().index_information()))  # 4 + _id
