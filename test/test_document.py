import unittest

from nanomongo.field import Field
from nanomongo.document import BaseDocument
from nanomongo.errors import ValidationError, ExtraFieldError, ConfigurationError

try:
    import pymongo
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

        [self.assertRaises(TypeError, func) for func in (bad_field, bad_field_default)]

    def test_document_bad_init(self):
        """Test incorrect document init"""

        class Doc(BaseDocument):
            pass
        self.assertRaises(TypeError, Doc, *(1,))
        self.assertRaises(ExtraFieldError, Doc, *({'foo': 'bar'},))
        self.assertRaises(ExtraFieldError, Doc, **{'foo': 'bar'})

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

        [self.assertRaises(TypeError, func) for func in (bad_client, bad_db, bad_col)]

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
        self.assertEqual('nanomongotest', d.nanomongo.database)
        self.assertEqual('nanomongotest', dd.nanomongo.database)
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


class MongoDocumentTestCase(unittest.TestCase):
    def setUp(self):
        pymongo.MongoClient().drop_database('nanotestdb')

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_save_find(self):
        """Pymongo: Test document save, find, find_one"""
        client = pymongo.MongoClient()

        class Doc(BaseDocument, dot_notation=True, client=client, db='nanotestdb'):
            foo = Field(str)
            bar = Field(int, required=False)

        self.assertEqual(None, Doc.find_one())
        d = Doc(foo='foo value')
        d.bar = 'wrong type'
        self.assertRaises(ValidationError, d.save)
        d.bar = 42
        self.assertTrue(d.save())
        self.assertEqual(0, Doc.find({'foo': 'inexistent'}).count())
        self.assertEqual(1, Doc.find({'foo': 'foo value'}).count())
        self.assertTrue(Doc.find_one()._id)
