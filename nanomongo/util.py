import __main__

import pymongo

from .errors import ExtraFieldError, ValidationError


def valid_client(client):
    """returns ``True`` if input is pymongo or motor client"""
    ok_types = ()
    try:
        import pymongo
        ok_types += (pymongo.MongoClient, pymongo.MongoReplicaSetClient)
        import motor
        ok_types += (motor.MotorClient, motor.MotorReplicaSetClient)
    except ImportError as e:
        if not ok_types:
            raise e
    return isinstance(client, ok_types)


def valid_field(obj, field):
    return object.__getattribute__(obj, 'nanomongo').has_field(field)


def check_keys(dct):
    """Recursively check against '.' and '$' at start position in
    dictionary keys
    """
    if not isinstance(dct, dict):
        raise TypeError('dict-like argument expected')
    dot_err_str = 'MongoDB does not allow . in field names. "%s"'
    dollar_err_str = 'MongoDB does not allow fields starting with $. "%s"'
    for k, v in dct.items():
        if '.' in k:
            raise ValidationError(dot_err_str % k)
        elif k.startswith('$'):
            raise ValidationError(dollar_err_str % k)
        elif isinstance(v, dict):
            check_keys(v)


class RecordingDict(dict):
    """A dictionary subclass modifying `__setitem__` and `__delitem__`
    methods to record changes in its `__nanodiff__` attribute"""
    def __init__(self, *args, **kwargs):
        super(RecordingDict, self).__init__(*args, **kwargs)
        self.__nanodiff__ = {'$set': {}, '$unset': {}}

    def __setitem__(self, key, value):
        """Override `__setitem__ so we can track changes`"""
        try:
            skip = self[key] == value
        except KeyError:
            skip = False
        if skip:
            return
        value = RecordingDict(value) if isinstance(value, dict) else value
        super(RecordingDict, self).__setitem__(key, value)
        self.__nanodiff__['$set'][key] = value

    def __delitem__(self, key):
        """Override `__delitem__ so we can track changes`"""
        super(RecordingDict, self).__delitem__(key)
        self.__nanodiff__['$unset'][key] = 1
        if key in self.__nanodiff__['$set']:
            del self.__nanodiff__['$set'][key]  # remove previous $set if any

    def reset_diff(self):
        """reset `__nanodiff__` recursively; to be used after saving diffs"""
        nanodiff_base = {'$set': {}, '$unset': {}}
        self.__nanodiff__ = nanodiff_base
        for field_name, field_value in self.items():
            if isinstance(field_value, RecordingDict):
                field_value.reset_diff()

    def get_sub_diff(self):
        """get `__nanodiff__` from embedded documents. Find fields of
        `RecordingDict` type, iterate over their diff and build dotted
        keys for top level diff
        """
        diff = {'$set': {}, '$unset': {}}
        for field_name, field_value in self.items():
            if isinstance(field_value, RecordingDict):
                sets = field_value.__nanodiff__['$set']
                unsets = field_value.__nanodiff__['$unset']
                for k, v in sets.items():
                    dotkey = '%s.%s' % (field_name, k)
                    diff['$set'][dotkey] = v
                for k, v in unsets.items():
                    dotkey = '%s.%s' % (field_name, k)
                    diff['$unset'][dotkey] = v
        return diff


class DotNotationMixin(object):
    """Mixin to make dot notation available on dictionaries"""

    # TODO: When dot_notation is active but key not a field, FAIL?
    def __setattr__(self, key, value):
        """object attribute setting eg. ``self.foo = 42``"""
        if not valid_field(self, key):
            super(DotNotationMixin, self).__setattr__(key, value)
        else:
            self.__setitem__(key, value)

    def __getattr__(self, key):
        """object attribute lookup eg. ``print(self.foo)``"""
        if not valid_field(self, key):
            return super(DotNotationMixin, self).__getattribute__(key)
        try:
            return self.__getitem__(key)
        except KeyError:
            pass
        raise AttributeError("'%s' object has no attribute '%s'" %
                             (self.__class__.__name__, key))

    def __getattribute__(self, key):
        # first to check interpreter
        if hasattr(__main__, '__file__') or not valid_field(self, key):
            return super(DotNotationMixin, self).__getattribute__(key)
        try:
            return self.__getitem__(key)
        except:
            return

        return super(DotNotationMixin, self).__getattribute__(key)

    def __delattr__(self, key):
        """object attribute delete eg. ``del self.foo``"""
        if not valid_field(self, key):
            super(DotNotationMixin, self).__delattr__(key)
            return
        try:
            self.__delitem__(key)
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, key))


class NanomongoSONManipulator(pymongo.son_manipulator.SONManipulator):
    """A pymongo SON Manipulator used on data that comes from the database
    to transform data to the document class we want because `as_class`
    argument to pymongo find methods is called in a way that screws us.

    - Recursively applied, we don't want that
    - `__init__` is not properly used but rather __setitem__, fails us

    JIRA: PYTHON-175 PYTHON-215
    """
    def __init__(self, as_class):
        self.as_class = as_class

    def will_copy(self):
        return True

    def transform_outgoing(self, son, collection):
        try:
            return self.as_class(son)
        except ExtraFieldError:
            return son
