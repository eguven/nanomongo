from .errors import ValidationError, ExtraFieldError
from .field import Field
from .util import DotNotationMixin

class BasesTuple(tuple): pass

class Nanomongo(object):
    def __init__(self, fields=None):
        super(Nanomongo, self).__init__()
        if not isinstance(fields, dict):
            raise TypeError('fields kwarg expected of type dict')
        self.fields = fields

    @classmethod
    def from_dicts(cls, *args):
        """Create from dict, filtering relevant items"""
        if not args:
            raise TypeError('from_dicts takes at least 1 positional argument')
        fields = {}
        for dct in args:
            if not isinstance(dct, dict):
                raise TypeError('expected input of dictionaries')
            for field_name, field_value in dct.items():
                if isinstance(field_value, Field):
                    fields[field_name] = field_value
        return cls(fields=fields)

    def has_field(self, key):
        """Check existence of field"""
        return key in self.fields

    def list_fields(self):
        """Return a list of strings denoting fields"""
        return list(self.fields.keys())

    def validate(self, field_name, value):
        """Validate field input"""
        return self.fields[field_name].validator(value, field_name=field_name)


class DocumentMeta(type):
    """Document Metaclass. Generates allowed field set and their validators
    """

    def __new__(cls, name, bases, dct, **kwargs):
        print('PRE', bases)
        use_dot_notation = kwargs.pop('dot_notation') if 'dot_notation' in kwargs else None
        if use_dot_notation:
            new_bases = (DotNotationMixin,) + cls._get_bases(bases)
        else:
            new_bases = cls._get_bases(bases)
        print('POST', new_bases)
        return super(DocumentMeta, cls).__new__(cls, name, new_bases, dct)

    def __init__(cls, name, bases, dct, **kwargs):
        # TODO: disallow nanomongo name
        # TODO: disallow duplicate names
        super(DocumentMeta, cls).__init__(name, bases, dct)
        print(dct,'\n')
        if hasattr(cls, 'nanomongo'):
            cls.nanomongo = Nanomongo.from_dicts(cls.nanomongo.fields, dct)

        else:
            cls.nanomongo = Nanomongo.from_dicts(dct)
        for field_name, field_value in dct.items():
            if isinstance(field_value, Field): delattr(cls, field_name)


    @classmethod
    def _get_bases(cls, bases):
        # taken from MongoEngine
        if isinstance(bases, BasesTuple):
            return bases
        seen = []
        bases = cls.__get_bases(bases)
        unique_bases = (b for b in bases if not (b in seen or seen.append(b)))
        return BasesTuple(unique_bases)

    @classmethod
    def __get_bases(cls, bases):
        for base in bases:
            if base is object:
                continue
            yield base
            for child_base in cls.__get_bases(base.__bases__):
                yield child_base
        

class BaseDocument(dict, metaclass=DocumentMeta):
    """BaseDocument class. Subclasses to be used."""

    def __init__(self, *args, **kwargs):
        print('ARGS:', args, 'KWARGS:', kwargs)
        # if input dict, merge (not updating) into kwargs
        if args and not isinstance(args[0], dict):
            raise TypeError('dict or subclass argument expected')
        elif args:
            for field_name, field_value in args[0].items():
                if field_name not in kwargs:
                    kwargs[field_name] = field_value
        print('KWARGS:', kwargs)
        dict.__init__(self, *args, **kwargs)
        for field_name, field in self.nanomongo.fields.items():
            if hasattr(field, 'default_value'):
                val = field.default_value
                self[field_name] = val() if callable(val) else val
        for field_name in kwargs:
            if self.nanomongo.has_field(field_name):
                self.nanomongo.validate(field_name, kwargs[field_name])
                self[field_name] = kwargs[field_name]
            else:
                raise ExtraFieldError('Undefined field %s=%s in %s' %
                                      (field_name, kwargs[field_name], self.__class__))

    def __dir__(self):
        """Add defined Fields to dir"""
        return sorted(super(BaseDocument, self).__dir__() + self.nanomongo.list_fields())

    def validate(self):
        """Override to add extra validation"""
        pass

    def validate_all(self):
        """Check against extra fields, run field validators and user-defined validate"""
        for field, value in self.items():
            if not self.nanomongo.has_field(field):
                raise ValidationError('extra field "%s" with value "%s"' % (field, value))
        for field_name, field in self.nanomongo.fields.items():
            if field_name in self:
                field.validator(self[field_name], field_name=field_name)
            elif field.required:
                raise ValidationError('required field "%s" missing' % field_name)
        return self.validate()

class Doc(BaseDocument, dot_notation=True):
    name = Field(str)
    no = Field(int)

class Doc2(Doc):
    name = Field(str)
    lol = Field(int, default=42)
