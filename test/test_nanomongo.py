import unittest

from nanomongo.field import Field
from nanomongo.document import Nanomongo


class NanomongoTestCase(unittest.TestCase):
    def test_nanomongo_inits(self):
        self.assertRaises(TypeError, Nanomongo, *(1,))
        self.assertRaises(TypeError, Nanomongo, **{'foo': 'bar'})
        self.assertRaises(TypeError, Nanomongo, **{'fields': 'bar'})
        self.assertRaises(TypeError, Nanomongo.from_dicts)
        self.assertRaises(TypeError, Nanomongo.from_dicts, *(1,))
        fields_1 = {'foo': Field(str)}
        fields_2 = {'foo': Field(str), 'bar': Field(int)}
        nano_1 = Nanomongo(fields=fields_1)
        nano_2 = Nanomongo.from_dicts(fields_1, fields_2)
        self.assertEqual(['foo'], nano_1.list_fields())
        self.assertEqual(['bar', 'foo'], nano_2.list_fields())
