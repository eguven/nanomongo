import __main__

import pymongo


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


class RecordingDict(dict):
    """A dictionary subclass modifying `__setitem__` and `__delitem__`
    methods to record changes in its `__nanodiff__` attribute"""
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.__nanodiff__ = {'$set': {}, '$unset': {}}

    def __setitem__(self, key, value):
        """Override `__setitem__ so we can track changes`"""
        #print(key, value) if not self else None
        super(RecordingDict, self).__setitem__(key, value)
        self.__nanodiff__['$set'][key] = value

    def __delitem__(self, key):
        """Override `__delitem__ so we can track changes`"""
        super(RecordingDict, self).__delitem__(key)
        self.__nanodiff__['$unset'][key] = 1
        if key in self.__nanodiff__['$set']:
            del self.__nanodiff__['$set'][key]  # remove previous $set if any

    def reset_diff(self):
        """reset `__nanodiff__` to be used after saving diffs"""
        self.__nanodiff__ = {'$set': {}, '$unset': {}}


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
        return self.as_class(son)
