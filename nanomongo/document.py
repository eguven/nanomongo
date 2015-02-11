import importlib
import weakref

import pymongo
import six

from bson import ObjectId, DBRef

from .errors import *
from .field import Field
from .util import (
    RecordingDict, DotNotationMixin, valid_client, NanomongoSONManipulator,
    check_spec,
)


def ref_getter_maker(field_name, document_class=None):
    """create dereference methods for given ``field_name`` to be bound
    to Document instances
    """
    def ref_getter(self):
        if field_name not in self or not self[field_name]:
            raise DBRefNotSetError('"%s" field is not set' % field_name)
        dbref = self[field_name]
        if document_class is not None:
            splat = document_class.split('.')
            class_name = splat.pop()
            module = '.'.join(splat) if splat else self.__class__.__module__
            cls = getattr(importlib.import_module(module), class_name)
        else:
            database = dbref.database if dbref.database else self.nanomongo.database
            collection = dbref.collection
            filter_f = (lambda cls: cls.nanomongo.registered and
                        cls.nanomongo.database.name == database and
                        cls.nanomongo.collection == collection)
            classes = list(filter(filter_f, BaseDocument.__subclasses__()))
            if 1 != len(classes):
                err_str = ('can not guess document class for "%s", found: "%s". '
                           'Please provide document_class kwarg to "%s" Field')
                raise UnsupportedOperation(err_str % (dbref, classes, field_name))
            cls = classes.pop()
        # we don't use dereference since BaseDocument.find_one handles type casting nicely
        return cls.find_one(_id=dbref.id)
    return ref_getter


class BasesTuple(tuple):
    pass


class Index(object):
    """A container for clean index definition, it's ``args`` and
    ``kwargs`` are passed to ``pymongo.Collection.create_index``
    """
    def __init__(self, *args, **kwargs):
        if not args:
            raise TypeError('Index: key or list of key-direction tuples expected')
        self.args = args
        self.kwargs = kwargs


class Nanomongo(object):
    """Contains information about the Document it's attached to like
    its fields (which contain validators), db and collection etc and
    provides methods to ease checks
    """
    def __init__(self, fields=None):
        super(Nanomongo, self).__init__()
        if not isinstance(fields, dict):
            raise TypeError('fields kwarg expected of type dict')
        self.fields = fields
        self.classref = None
        self.registered = False
        self.client, self.database, self.collection = None, None, None
        self.transforms = {}  # save auto_update fields so we don't keep looping
        for field_name, field in self.fields.items():
            if hasattr(field, 'auto_update'):
                self.transforms[field_name] = field.auto_update

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
        return sorted(self.fields.keys())

    def validate(self, field_name, value):
        """Validate field input"""
        return self.fields[field_name].validator(value, field_name=field_name)

    def set_client(self, client):
        """Set client, a Client from pymongo or motor expected"""
        if not valid_client(client):
            raise TypeError('pymongo or motor Client expected')
        self.client = client

    def set_db(self, db_string):
        """Set database, string expected"""
        if not db_string or not isinstance(db_string, six.string_types):
            raise TypeError('Exected database string')
        if not self.client:
            raise ConfigurationError('Mongo client not set')
        self.database = self.client[db_string]

    def set_collection(self, col_string):
        """Set collection, string expected"""
        if not col_string or not isinstance(col_string, six.string_types):
            raise TypeError('Expected collection string')
        self.collection = col_string

    def check_config(self):
        """Check if client, database and collection attributes are set"""
        if not self.client:
            raise ConfigurationError('Mongo client not set')
        elif not self.database:
            raise ConfigurationError('database not set')
        elif not self.collection:
            raise ConfigurationError('collection not set')

    def add_son_manipulator(self):
        """add our son manipulator to transform documents coming from mongodb
        to the class we defined, see
        :class:`~nanomongo.util.NanomongoSONManipulator`
        """
        if six.PY2:  # unicode -> str implicit transform for binary_type (str) Fields
            def str_transformer(unicode_str):
                return unicode_str.encode('utf-8')

            str_fields = ((fname, field) for fname, field in self.fields.items()
                          if six.binary_type == field.data_type)
            transforms = dict((fname, str_transformer) for fname, field in str_fields)
        else:
            transforms = None

        manipulator = NanomongoSONManipulator(self.classref(), transforms=transforms)
        self.database.add_son_manipulator(manipulator)

    def register(self, client=None, db_string=None, collection=None):
        """register the class. this is called from defined documents'
        :meth:`~BaseDocument.register()` method. Note that this also
        runs :meth:`~pymongo.collection.Collection.ensure_index()`
        """
        self.set_client(client) if client else None
        self.set_db(db_string) if db_string else None
        self.set_collection(collection) if collection else None
        self.check_config()
        self.add_son_manipulator()
        # indexes
        doc_class = self.classref()
        indexes = doc_class.__indexes__ if hasattr(doc_class, '__indexes__') else []
        for index in indexes:
            self.ensure_index(index)
        if hasattr(doc_class, '__indexes__'):
            delattr(doc_class, '__indexes__')
        # mark as registered
        self.registered = True

    def get_collection(self):
        """Returns collection"""
        self.check_config()
        return self.database[self.collection]

    def ensure_index(self, index):
        """``Collection.ensure_index`` wrapper"""
        return self.get_collection().ensure_index(*index.args, **index.kwargs)


class DocumentMeta(type):
    """Document Metaclass. Generates allowed field set and their validators
    """

    def __new__(cls, name, bases, dct, **kwargs):
        """Check against illegal attributes (eg. ``nanomongo``); get bases
        so we can get their :class:`~nanomongo.field.Field` definitions
        """
        if 'nanomongo' in dct:
            raise TypeError('field name "nanomongo" is not allowed')
        if '__indexes__' in dct and not isinstance(dct['__indexes__'], list):
            raise TypeError('__indexes__: list of Index instances expected')
        use_dot_notation = kwargs.pop('dot_notation') if 'dot_notation' in kwargs else None
        if 'dot_notation' in dct:
            use_dot_notation = dct.pop('dot_notation')
        new_bases = cls._get_bases(bases)
        if use_dot_notation and DotNotationMixin not in new_bases:
            new_bases = (DotNotationMixin,) + new_bases
        return super(DocumentMeta, cls).__new__(cls, name, new_bases, dct)

    def __init__(cls, name, bases, dct, **kwargs):
        """Create the `~nanomongo.document.Nanomongo` for this class and delete
        :class:`~nanomongo.field.Field` attributes. Also sets client, db, collection
        info if provided and runs indexes"""
        super(DocumentMeta, cls).__init__(name, bases, dct)
        if hasattr(cls, 'nanomongo'):
            cls.nanomongo = Nanomongo.from_dicts(cls.nanomongo.fields, dct)
        else:
            cls.nanomongo = Nanomongo.from_dicts(dct)
        if not cls.nanomongo.has_field('_id'):
            cls.nanomongo.fields['_id'] = Field(ObjectId, required=False)
        for field_name, field_value in dct.items():
            if isinstance(field_value, Field):
                delattr(cls, field_name)
        # client, database, collection
        cls.nanomongo.classref = weakref.ref(cls)

        def _check_arg(arg):
            return arg in kwargs or hasattr(cls, arg)

        def _get_arg(arg):
            """get arg from kwargs or from class attribute and
            remove class attribute"""
            if arg in kwargs:
                return kwargs[arg]
            retval = getattr(cls, arg)
            delattr(cls, arg)
            return retval

        if _check_arg('client'):
            cls.nanomongo.set_client(_get_arg('client'))
        if _check_arg('db'):
            cls.nanomongo.set_db(_get_arg('db'))
        if _check_arg('collection'):
            cls.nanomongo.set_collection(_get_arg('collection'))
        else:
            cls.nanomongo.set_collection(name.lower())
        # register if nanomongo config is OK
        try:
            cls.nanomongo.check_config()
            cls.nanomongo.register()
        except ConfigurationError:
            pass
        # indexes
        indexes = cls.__indexes__ if hasattr(cls, '__indexes__') else []

        for index in indexes:
            if not isinstance(index, Index):
                raise TypeError('__indexes__: list of Index instances expected')
            cls.check_index(index)

    def check_index(cls, index):
        """check correctness of :class:`~Index` definitions"""
        def valid_index_key(ikey):
            if '.' not in ikey:
                return cls.nanomongo.has_field(ikey)
            field = ikey.split('.')[0]
            return (cls.nanomongo.has_field(field) and
                    cls.nanomongo.fields[field].data_type in [dict, list])
        i = index.args[0]  # key or list
        if not isinstance(i, (six.string_types, list)):
            raise TypeError('Index: str or list of key-value tuples expected')
        if isinstance(i, six.string_types) and not valid_index_key(i):
            raise IndexMismatchError('field for index "%s" does not exist' % i)
        elif isinstance(i, list):
            for tup in i:
                if not isinstance(tup, tuple) or 2 != len(tup):
                    raise TypeError('Index: list of key-value tuples expected')
                if not valid_index_key(tup[0]):
                    err_str = 'field for index "%s" does not exist' % tup[0]
                    raise IndexMismatchError(err_str)

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


@six.add_metaclass(DocumentMeta)
class BaseDocument(RecordingDict):
    """BaseDocument class. Subclasses should be used. See
    :meth:`~BaseDocument.__init__()`
    """

    def __init__(self, *args, **kwargs):
        """Inits the document with given data and validates the fields
        (field validation bad idea during init?). If you define
        ``__init__`` method for your document class, make sure to call
        this
        ::

            class MyDoc(BaseDocument, dot_notation=True):
                foo = Field(str)
                bar = Field(int, required=False)

                def __init__(self, *args, **kwargs):
                    super(MyDoc, self).__init__(*args, **kwargs)
                    # do other stuff
        """
        # if input dict, merge (not updating) into kwargs
        if args and not isinstance(args[0], dict):
            raise TypeError('dict or dict subclass argument expected')
        elif args:
            for field_name, field_value in args[0].items():
                if field_name not in kwargs:
                    kwargs[field_name] = field_value
        super(BaseDocument, self).__init__()
        for field_name, field in self.nanomongo.fields.items():
            if hasattr(field, 'default_value'):
                val = field.default_value
                dict.__setitem__(self, field_name, val() if callable(val) else val)
            # attach get_<field_name>_field methods for DBRef fields
            if field.data_type in [DBRef] + DBRef.__subclasses__():
                getter_name = 'get_%s_field' % field_name
                doc_class = field.document_class if hasattr(field, 'document_class') else None
                getter = ref_getter_maker(field_name, document_class=doc_class)
                setattr(self, getter_name, six.create_bound_method(getter, self))
        for field_name in kwargs:
            if self.nanomongo.has_field(field_name):
                self.nanomongo.validate(field_name, kwargs[field_name])
                dict.__setitem__(self, field_name, kwargs[field_name])
            else:
                raise ExtraFieldError('Undefined field %s=%s in %s' %
                                      (field_name, kwargs[field_name], self.__class__))
        for field_name, field_value in self.items():
            # transform dict to RecordingDict so we can track diff in embedded docs
            if isinstance(field_value, dict):
                dict.__setitem__(self, field_name, RecordingDict(field_value))

    @classmethod
    def register(cls, client=None, db=None, collection=None):
        """Register this document. Sets client, database, collection
        information, builds (ensure) indexes and sets SON manipulator
        """
        if cls.nanomongo.registered:
            err_str = '''%s is already registered. This is automatic if you have defined
your document class with client, db, collection.''' % cls
            raise ConfigurationError(err_str)
        cls.nanomongo.register(client=client, db_string=db, collection=collection)

    @classmethod
    def get_collection(cls):
        """Returns collection as set in :attr:`~cls.nanomongo`"""
        return cls.nanomongo.get_collection()

    @classmethod
    def find(cls, *args, **kwargs):
        """``pymongo.Collection().find`` wrapper for this document"""
        if args:
            check_spec(cls, args[0])
        return cls.get_collection().find(*args, **kwargs)

    @classmethod
    def find_one(cls, *args, **kwargs):
        """``pymongo.Collection().find_one`` wrapper for this document"""
        if args:
            check_spec(cls, args[0])
        return cls.get_collection().find_one(*args, **kwargs)

    def __dir__(self):
        """Add defined Fields to dir"""
        return sorted(dir(super(BaseDocument, self)) + self.nanomongo.list_fields())

    def validate(self):
        """Override this to add extra document validation, will be
        called at the end of :meth:`~validate_all()` """
        pass

    def validate_all(self):
        """Check against extra fields, run field validators and
        user-defined :meth:`~validate()` """
        for field, value in self.items():
            if not self.nanomongo.has_field(field):
                raise ValidationError('extra field "%s" with value "%s"' % (field, value))
        for field_name, field in self.nanomongo.fields.items():
            if field_name in self:
                field.validator(self[field_name], field_name=field_name)
            elif field.required:
                raise ValidationError('required field "%s" missing' % field_name)
        return self.validate()

    def validate_diff(self):
        """Check correctness of diffs before partial update, also run
        user-defined :meth:`~validate()` """
        sets = self.__nanodiff__['$set']
        unsets = self.__nanodiff__['$unset']
        for field_name, field_value in unsets.items():
            if self.nanomongo.has_field(field_name):
                if self.nanomongo.fields[field_name].required:
                    raise ValidationError('can not unset "%s", required' % field_name)
        for field_name, field_value in sets.items():
            if not self.nanomongo.has_field(field_name):
                err_str = 'extra field "%s" with value "%s"'
                raise ValidationError(err_str % (field_name, field_value))
            field = self.nanomongo.fields[field_name]
            field.validator(field_value, field_name=field_name)
        return self.validate()

    def run_auto_updates(self):
        """Runs functions in :attr:`nanomongo.transforms` like
        auto_update stuff before :meth:`~insert()` :meth:`~save()`
        """
        for field_name, updater in self.nanomongo.transforms.items():
            self[field_name] = updater()

    def insert(self, **kwargs):
        """Insert document into database, return _id. Runs
        :meth:`~run_auto_updates()` and :meth:`~validate_all()` """
        self.run_auto_updates()
        self.validate_all()
        id_or_ids = self.get_collection().insert(self, **kwargs)
        self.reset_diff()
        for field_name, field_value in self.items():
            if isinstance(field_value, dict):  # cast dicts
                field_value = RecordingDict(field_value)
        return id_or_ids

    def save(self, **kwargs):
        """Saves document. This method only does partial updates and no
        inserts. Runs :meth:`~run_auto_updates()` and :meth:`~validate_all()`
        prior to save. Returns ``Collection.update()`` response
        """
        if '_id' not in self:
            raise ValidationError('insert first; save does partial updates')
        if '_id' in self.__nanodiff__['$set']:
            raise ValidationError('_id seems to be manually set, do insert')
        self.run_auto_updates()
        self.validate_diff()
        assert 3 == len(self.__nanodiff__), '__nanodiff__: %s' % self.__nanodiff__
        query = {'_id': self['_id']}
        diff = self.__nanodiff__
        # get subdiff containing dotted keys, merge into diff
        subdiff = self.get_sub_diff()
        diff['$set'].update(subdiff['$set'])
        diff['$unset'].update(subdiff['$unset'])
        diff['$addToSet'].update(subdiff['$addToSet'])
        # remove empty update ops, MongoDB 2.6 returns error for them
        diff = dict(filter(lambda update: update[1], diff.items()))
        # for operation in ('$set', '$unset', '$addToSet'):
        #     if {} == diff[operation]:
        #         del diff[operation]
        if not diff:
            self.reset_diff()
            return
        response = self.get_collection().update(query, diff, **kwargs)
        self.reset_diff()
        return response

    def addToSet(self, field, value):
        """MongoDB ``Collection.update()`` $addToSet functionality.
        This sets the value accordingly and records the change in
        :attr:`~__nanodiff__` to be saved with :meth:`~save()`.
        ::

            # MongoDB style dot notation can be used to add to lists
            # in embedded documents
            doc = Doc(foo=[], bar={})
            doc.addToSet('foo', new_value)
            doc.addToSet('bar.sub_field', new_value)

        Contrary to how $set has no effect under __setitem__ (see
        :class:`~.util.RecordingDict`.__setitem__) when the
        new value is equal to the current; $addToSet explicitly adds
        the call to :attr:`~__nanodiff__` so it will be sent to the
        database when :meth:`save()` is called.
        """
        def top_level_add(self, field, value):
            """add the value to field. appending if the list exists and
            does not contain the value; create new list otherwise.
            raise :class:`.errors.ValidationError` if non-list value initiated
            """
            self.check_can_update('$addToSet', field)
            if field in self and isinstance(self[field], list):
                if value not in self[field]:
                    self[field].append(value)
            elif field not in self or self[field] is None:
                dict.__setitem__(self, field, [value])  # to avoid $set record
            else:
                err_str = 'Could not $addToSet on valid field, bad init? %s: %s'
                raise ValidationError(err_str % (field, self[field]))
            if field not in self.__nanodiff__['$addToSet']:
                self.__nanodiff__['$addToSet'][field] = {'$each': [value]}
            elif value not in self.__nanodiff__['$addToSet'][field]['$each']:
                self.__nanodiff__['$addToSet'][field]['$each'].append(value)

        if field.startswith('$') or '.$' in field:
            err_str = 'MongoDB does not allow fields starting with $. "%s"'
            raise ValidationError(err_str % field)
        # if top-level
        if '.' not in field:
            if ((self.nanomongo.has_field(field) and
                 list == self.nanomongo.fields[field].data_type)):
                top_level_add(self, field, value)  # add & record
            elif self.nanomongo.has_field(field):
                err_str = 'Cannot apply $addToSet modifier to non-array: %s=%s'
                err_str = err_str % (field, self.nanomongo.fields[field].data_type)
                raise ValidationError(err_str)
            else:
                raise ValidationError('Undefined field: "%s"' % top_key)
        # if deep-level
        else:
            try:
                top_key, deep_key = field.split('.')
            except ValueError:
                err_str = '''Only top level and one level deep keus supported for \
$addToSet: "%s"'''
                raise UnsupportedOperation(err_str, field)
            if not self.nanomongo.has_field(top_key):
                raise ValidationError('Undefined field: "%s"' % top_key)
            elif dict != self.nanomongo.fields[top_key].data_type:
                raise ValidationError('"%s" is not a dict' % top_key)
            # field name ok, ensure top level value is RecordingDict type
            if top_key not in self:  # not set yet, do it
                dict.__setitem__(self, top_key, RecordingDict())
            elif not isinstance(self[top_key], RecordingDict):
                # what did you do, use dict.__setitem__ ? :)
                err_str = '''Dotted key's target is not a RecordingDict: %s=%s \
If you've just set it as a new dict; FYI: you can't $set and $addToSet together'''
                raise ValidationError(err_str % (top_key, self[top_key]))
            # make sure we have no $set or $unset on top_key
            self.check_can_update('$addToSet', top_key)
            top_level_add(self[top_key], deep_key, value)  # add & record

    def get_dbref(self):
        """create a ``bson.DBRef`` instance for this :class:`BaseDocument`
        instance
        """
        assert '_id' in self and self['_id'], 'Cannot get DBRef for document with no _id'
        collection = self.get_collection()
        return DBRef(collection.name, self['_id'], database=collection.database.name)
