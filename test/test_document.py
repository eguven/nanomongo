import unittest

from nanomongo import Field, BaseDocument
from nanomongo.errors import ValidationError

class DocumentTestCase(unittest.TestCase):
    def test_document_bad_field(self):

        def bad_field():
            class Doc(BaseDocument):
                foo = Field()

        def bad_field_default():
            class Doc(BaseDocument):
                foo = Field(str, default=1)

        [self.assertRaises(TypeError, func) for func in (bad_field, bad_field_default)]

    def test_document(self):

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