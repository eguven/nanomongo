import __main__
import logging
import warnings

import pymongo

from pymongo import son_manipulator

from .errors import ExtraFieldError, ValidationError

ok_types = ()

try:
    import pymongo
    ok_types += (pymongo.MongoClient, pymongo.MongoReplicaSetClient)
    import motor
    ok_types += (motor.MotorClient, motor.MotorReplicaSetClient)
except ImportError as e:
    if not ok_types:
        raise e

logging.basicConfig(format='[%(asctime)s] %(levelname)s [%(module)s.%(funcName)s():%(lineno)d] %(message)s')
logger = logging.getLogger(__file__)


def valid_client(client):
    """returns ``True`` if input is pymongo or motor client
    or any client added with allow_client()"""
    return isinstance(client, ok_types)


def allow_client(client_type):
    """Allows another type to act as client type.
    Intended for using with mock clients."""
    global ok_types
    ok_types += (client_type,)


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


def check_spec(cls, spec):
    """Check the query spec for given class & display warnings.
    Dotted keys are checked for top-level field existence and its type
    being dict/list. Normal keys are checked for field existence only.
    """
    w_field = '{0} has no field "{1}", can not match'
    w_field_type = '{0} field "{1}" is not of type {2}, can not match'
    for field in spec.keys():
        f = field.split('.')[0]
        if not cls.nanomongo.has_field(f):
            logging.warn(w_field.format(cls, f))
        elif '.' in field:
            dtype = cls.nanomongo.fields[f].data_type
            if dtype not in (dict, list):
                logging.warn(w_field_type.format(cls, f, (dict, list)))


class RecordingDict(dict):
    """A dictionary subclass modifying :meth:`~__setitem__()` and
    :meth:`~__delitem__()` methods to record changes in its
    :attr:`~__nanodiff__` attribute"""
    def __init__(self, *args, **kwargs):
        super(RecordingDict, self).__init__(*args, **kwargs)
        self.__nanodiff__ = {
            '$set': {}, '$unset': {}, '$addToSet': {},
        }

    def __setitem__(self, key, value):
        """Override :meth:`~dict.__setitem__` so we can track changes"""
        try:
            skip = self[key] == value
        except KeyError:
            skip = False
        if skip:
            return
        value = RecordingDict(value) if isinstance(value, dict) else value
        super(RecordingDict, self).__setitem__(key, value)
        self.__nanodiff__['$set'][key] = value
        self.clean_other_modifiers('$set', key)

    def __delitem__(self, key):
        """Override :meth:`~dict.__delitem__` so we can track changes"""
        super(RecordingDict, self).__delitem__(key)
        self.__nanodiff__['$unset'][key] = 1
        self.clean_other_modifiers('$unset', key)

    def clean_other_modifiers(self, current_mod, field_name):
        """Given `current_mod`, removes other `field_name` modifiers,
        eg. when called with `$set`, removes `$unset` and `$addToSet`
        etc. on `field_name`
        """
        for mod, updates in self.__nanodiff__.items():
            if mod == current_mod:
                continue
            if field_name in updates:
                del self.__nanodiff__[mod][field_name]

    def reset_diff(self):
        """reset `__nanodiff__` recursively; to be used after saving
        diffs. This does NOT do a rollback. Reload from db for that
        """
        nanodiff_base = {'$set': {}, '$unset': {}, '$addToSet': {}}
        self.__nanodiff__ = nanodiff_base
        for field_name, field_value in self.items():
            if isinstance(field_value, RecordingDict):
                field_value.reset_diff()

    def get_sub_diff(self):
        """get `__nanodiff__` from embedded documents. Find fields of
        :class:`~RecordingDict` type, iterate over their diff and build dotted
        keys for top level diff
        """
        diff = {'$set': {}, '$unset': {}, '$addToSet': {}}
        for field_name, field_value in self.items():
            if isinstance(field_value, RecordingDict):
                sets = field_value.__nanodiff__['$set']
                unsets = field_value.__nanodiff__['$unset']
                addtosets = field_value.__nanodiff__['$addToSet']
                for k, v in sets.items():
                    dotkey = '%s.%s' % (field_name, k)
                    diff['$set'][dotkey] = v
                for k, v in unsets.items():
                    dotkey = '%s.%s' % (field_name, k)
                    diff['$unset'][dotkey] = v
                for k, v in addtosets.items():
                    dotkey = '%s.%s' % (field_name, k)
                    diff['$addToSet'][dotkey] = v
        return diff

    def check_can_update(self, modifier, field_name):
        """Check if given `modifier` `field_name` combination can be
        added. MongoDB does not allow field duplication with update
        modifiers. This is to be used with methods `addToSet` ...
        """
        for mod, updates in self.__nanodiff__.items():
            if mod == modifier:
                continue
            if field_name in updates:
                err_str = 'Field name duplication not allowed with modifiers '
                err_str += ('new: {%s} old: {%s: {%s: %s}}' %
                            (modifier, mod, field_name, updates[field_name]))
                raise ValidationError(err_str)


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
