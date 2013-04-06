import __main__

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