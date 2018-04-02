import unittest

from nanomongo.document import BaseDocument, Field
from nanomongo.errors import ConfigurationError

from . import PYMONGO_CLIENT


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

    @unittest.skipUnless(PYMONGO_CLIENT, 'pymongo not installed or connection refused')
    def test_document_register_configuration(self):
        """Test MongoDB client/db/collection config as class kwargs
        """

        class Doc(BaseDocument, client=PYMONGO_CLIENT, db='nanomongotest'):
            pass

        class Doc2(Doc, dot_notation=True, client=PYMONGO_CLIENT, db='nanomongotest', collection='othercollection'):
            pass

        self.assertTrue(Doc.nanomongo.registered)
        self.assertEqual(PYMONGO_CLIENT.nanomongotest.doc, Doc.get_collection())
        self.assertRaises(ConfigurationError, Doc.register,
                          **{'client': PYMONGO_CLIENT, 'db': 'nanomongotest'})
        self.assertEqual(PYMONGO_CLIENT.nanomongotest.othercollection, Doc2.get_collection())
