.. nanomongo documentation master file, created by
   sphinx-quickstart on Tue Apr 16 16:21:17 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nanomongo's documentation!
=====================================

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python. It does not attempt to be a feature-complete
ODM but if you enjoy using `PyMongo <https://api.mongodb.com/python/current>`_ API with dictionaries and often find yourself writing validators and
``pymongo.Collection`` wrappers, nanomongo might suit your needs.

**Quick Links**: `Source (github) <https://github.com/eguven/nanomongo>`_ - `Documentation (rtd) <https://nanomongo.readthedocs.org/>`_ - `Packages (PyPi) <https://pypi.python.org/pypi/nanomongo/>`_ - `Changelog <https://github.com/eguven/nanomongo/blob/master/CHANGELOG.md>`_

Installation
------------

.. code-block:: console

    $ pip install nanomongo

Quickstart
--------------

Defining A Document And Registering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can define a document as shown below::

    import pymongo
    from nanomongo import Field, BaseDocument


    class Py23Doc(BaseDocument):
        dot_notation = True  # to allow attribute-like access to document keys
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            pymongo.IndexModel('foo'),
            pymongo.IndexModel([('bar', 1), ('foo', -1)], unique=True),
        ]

    # before use, the document needs to be registered. The following will connect
    # to the database and create indexes if necessary
    Py23Doc.register(client=pymongo.MongoClient(), db='mydbname', collection='Py23Doc')

Python3 allows slightly cleaner definitions::

    # Python3 only
    class MyDoc(BaseDocument, dot_notation=True):
        foo = Field(str)
        bar = Field(int, required=False)

If you omit ``collection`` when defining/registering your document, ``__name__.lower()`` will
be used by default.

Creating, Inserting, Querying, Saving
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    doc = MyDoc(foo='1337', bar=42)  # creates document {'foo': '1337', 'bar': 42}
    doc.insert()                     # returns pymongo.results.InsertOneResult
    MyDoc.find_one({'foo': '1337'})  # returns document {'_id': ObjectId('...'), 'bar': 42, 'foo': '1337'}

    doc.foo = '42'                   # records the change
    del doc.bar                      # records the change
    # save only does partial updates, this will call
    # collection.update_one({'_id': doc['_id']}, {'$set': {'foo': '42'}, '$unset': {'bar': 1}})
    doc.save()                       # returns pymongo.results.UpdateResult

    MyDoc.find_one({'foo': '1337'})  # returns None
    MyDoc.find_one({'foo': '42'})    # returns document {'_id': ObjectId('...'), 'foo': '42'}

:meth:`~.document.BaseDocument.insert()` is a wrapper around
``pymongo.Collection.insert_one()`` and :meth:`~.document.BaseDocument.save()` is
a wrapper around ``pymongo.Collection.update_one()``. They pass along received
keyword arguments and have the same return value.

:meth:`~.document.BaseDocument.find()` and :meth:`~.document.BaseDocument.find_one()`
methods are wrappers around respective methods of ``pymongo.Collection`` with same
arguments and return values.

Extensive Example
-----------------

.. toctree::
    example


Advanced Features
-----------------

$addToSet
^^^^^^^^^

MongoDB ``$addToSet`` update modifier is very useful. nanomongo implements it.

:meth:`~.document.BaseDocument.add_to_set()` will do the `add-to-field-if-doesnt-exist`
on your document instance and record the change to be applied later when
:meth:`~.document.BaseDocument.save()` is called.

::

    import pymongo
    from nanomongo import Field, BaseDocument

    class NewDoc(BaseDocument, dot_notation=True):
        list_field = Field(list)
        dict_field = Field(dict)

    NewDoc.register(client=pymongo.MongoClient(), db='mydbname')
    doc_id = NewDoc(list_field=[42], dict_field={'foo':[]}).insert().inserted_id
    doc = NewDoc.find_one({'_id': doc_id})
    # {'_id': ObjectId('...'), 'dict_field': {'foo': []}, 'list_field': [42]}

    doc.add_to_set('list_field', 1337)
    doc.add_to_set('dict_field.foo', 'like a boss')
    doc.save()

Both of the above ``add_to_set`` calls are applied to the ``NewDoc`` instance like MongoDB does it eg.

  - create list field with new value if it doesn't exist
  - add new value to list field if it's missing (append)
  - complain if it is not a list field

When save is called, the following is called::

    update_one(
        {'_id': doc['_id']},
        {'$addToSet': {'list_field': {'$each': [1337]}}, 'dict_field.foo': {'$each': ['like a boss']}}
    )

Undefined fields or field type mismatch raises :class:`~.errors.ValidationError`::

    doc.add_to_set('dict_field.foo', 'like a boss')
    ValidationError: Cannot apply $addToSet modifier to non-array: dict_field=<class 'dict'>

QuerySpec check
^^^^^^^^^^^^^^^

:meth:`~.document.BaseDocument.find()` and :meth:`~.document.BaseDocument.find_one()`
runs a simple check against queries and logs warnings for queries that can not match.
See :func:`~.util.check_spec()` for details.

dbref_field_getters
^^^^^^^^^^^^^^^^^^^

Documents that define ``bson.DBRef`` fields automatically generate getter methods
through :func:`~.document.ref_getter_maker` where the generated methods
have names such as ``get_<field_name>_field``.
::

    class MyDoc(BaseDocument):
        # document_class with full path
        source = Field(DBRef, document_class='some_module.Source')
        # must be defined in same module as this will use
        # mydoc_instance.__class__.__module__
        destination = Field(DBRef, document_class='Destination')
        # autodiscover
        user = Field(DBRef)

nanomongo tries to guess the ``document_class`` if it's not provided by looking at
registered subclasses of :class:`~.document.BaseDocument`. If it matches more than one
(for example when two document classes use the same collection), it will raise
:class:`~.errors.UnsupportedOperation`.

pymongo & motor
---------------

**0.5.0 update**: motor support is currently not in a working state, this section is
kept for reference.

Throughout the documentation, ``pymongo`` is referenced but all features work the
same when using `motor <https://github.com/mongodb/motor>`_ transparently if you
register the document class with a ``motor.MotorClient``.
::

    import motor
    from nanomongo import Field, BaseDocument

    class MyDoc(BaseDocument, dot_notation=True):
        foo = Field(str)
        bar = Field(list, required=False)

    client = motor.MotorClient().open_sync()
    MyDoc.register(client=client, db='dbname')

    # and now some async motor queries (using @gen.engine)
    doc_id = yield motor.Op(MyDoc(foo=42).insert)
    doc = yield motor.Op(MyDoc.find_one, {'foo': 42})
    doc.add_to_set('bar', 1337)
    yield motor.Op(doc.save)

**Note** however that pymongo vs motor behaviour is not necessarily identical.
Asynchronous methods require ``tornado.ioloop.IOLoop``. For example,
:meth:`~.document.BaseDocument.register` runs ``ensure_index`` but the query will not be sent
to MongoDB until ``IOLoop.start()`` is called.

Contents
========

.. toctree::
   :titlesonly:

   document
   errors
   field
   util


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

