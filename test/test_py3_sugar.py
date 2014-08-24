import unittest

from nanomongo.document import BaseDocument, Field
from nanomongo.errors import ConfigurationError

try:
    import pymongo
    import bson
    pymongo.MongoClient()
    PYMONGO_OK = True
except:
    PYMONGO_OK = False


class PY3SugarTestCase(unittest.TestCase):
    def test_class_kwargs(self):
        """Test keyword arguments given at class definition eg.
        client, dot_notation etc.
        """
        class Doc(BaseDocument, dot_notation=True):
            foo = Field(str)

        d = Doc()
        self.assertRaises(AttributeError, lambda: d.foo)
        d.foo = 'bar'
        self.assertTrue('foo' in d and 'bar' is d.foo)

    @unittest.skipUnless(PYMONGO_OK, 'pymongo not installed or connection refused')
    def test_document_register_configuration(self):
        """Test MongoDB client/db/collection config as class kwargs
        """
        client = pymongo.MongoClient()

        class Doc(BaseDocument, client=client, db='nanomongotest'):
            pass

        class Doc2(Doc, dot_notation=True, client=client, db='nanomongotest',
                   collection='othercollection'):
            pass

        self.assertTrue(Doc.nanomongo.registered)
        self.assertEqual(client.nanomongotest.doc, Doc.get_collection())
        self.assertRaises(ConfigurationError, Doc.register,
                          **{'client': client, 'db': 'nanomongotest'})
        self.assertEqual(client.nanomongotest.othercollection, Doc2.get_collection())
