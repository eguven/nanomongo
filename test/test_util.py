import unittest

from nanomongo.field import Field
from nanomongo.document import BaseDocument
from nanomongo.util import DotNotationMixin, valid_field


class MixinTestCase(unittest.TestCase):
    def test_mixin(self):
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
