=========
nanomongo
=========

.. image:: https://travis-ci.org/eguven/nanomongo.png
        :target: https://travis-ci.org/eguven/nanomongo

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python. It does not attempt to be a feature-complete
ODM but if you enjoy using PyMongo_ API with dictionaries and often find yourself writing validators and
``pymongo.Collection`` wrappers, nanomongo might suit your needs.

**Quick Links**: `Source (github) <https://github.com/eguven/nanomongo>`_ - `Documentation (rtd) <https://nanomongo.readthedocs.org/>`_ - `Packages (PyPi) <https://pypi.python.org/pypi/nanomongo/>`_ - `Changelog <https://github.com/eguven/nanomongo/blob/master/CHANGELOG.md>`_

Quickstart
-----------

::

    import pymongo
    from nanomongo import Field, BaseDocument

    client = pymongo.MongoClient()

    # python3 notation, see documentation for python2 options
    # we can omit the keyword arguments here and later call MyDoc.register(client=client, db='dbname')
    class MyDoc(BaseDocument, dot_notation=True, client=client, db='dbname'):
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            pymongo.IndexModel('foo'),
            pymongo.IndexModel([('bar', 1), ('foo', -1)], unique=True),
        ]

    doc = MyDoc(foo='L33t')  # creates document {'foo': 'L33t'}
    doc.insert()             # inserts document {'_id': ObjectId('...'), 'foo': 'L33t'}
    doc.bar = 42             # records the change
    doc.save()               # calls collection.update_one {'$set': {'bar': 42}}

    MyDoc.find_one({'foo': 'L33t'})
    {'_id': ObjectId('...'), 'bar': 42, 'foo': 'L33t'}

:Author: Eren Güven (GitHub_, Twitter_)
:License: `Apache License 2.0 <https://github.com/eguven/nanomongo/blob/master/LICENSE>`_

.. _PyMongo: https://api.mongodb.com/python/current
.. _GitHub: https://github.com/eguven
.. _Twitter: https://twitter.com/cyberfart
