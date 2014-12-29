.. nanomongo documentation master file, created by
   sphinx-quickstart on Tue Apr 16 16:21:17 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nanomongo's documentation!
=====================================

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python.
It does not attempt to be a feature-complete ODM but if you like
using ``pymongo`` api with python dictionaries and often find yourself
writing validators and ``pymongo.Collection`` wrappers, nanomongo
might suit your needs.

nanomongo has full test coverage.

**Quick Links**: `Source (github) <https://github.com/eguven/nanomongo>`_ - `Documentation (rtd) <https://nanomongo.readthedocs.org/>` - `Packages (PyPi) <https://pypi.python.org/pypi/nanomongo/>`

**Version 0.3**: nanomongo is now python2 compatible (with syntactic difference
when defining your Document, see `Defining Your Document`_ below).

Installation
------------

.. code-block:: console

    $ pip install nanomongo

or from git repo:

.. code-block:: console

    $ pip install git+https://github.com/eguven/nanomongo

Quick Tutorial
--------------

Defining Your Document
^^^^^^^^^^^^^^^^^^^^^^

::

    import pymongo
    from nanomongo import Index, Field, BaseDocument

    mclient = pymongo.MongoClient()

    class Py23CompatibleDoc(BaseDocument):
        client = mclient
        db = 'dbname'
        dot_notation = True
        foo = Field(str)
        bar = Field(int, required=False)

    # Python3 only
    class Py3Doc(BaseDocument, dot_notation=True, client=mclient, db='dbname'):
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            Index('foo'),
            Index([('bar', 1), ('foo', -1)], unique=True),
        ]

You don't have to declare ``client`` or ``db`` like this, you can
:meth:`~.document.BaseDocument.register` (and I definitely prefer it on
python2) your document later as such:

::

    client = pymongo.MongoClient()
    MyDoc.register(client=client, db='dbname', collection='mydoc')

If you omit ``collection`` when defining/registering your document,
``__name__.lower()`` will be used by default

Creating, Inserting, Saving
^^^^^^^^^^^^^^^^^^^^^^^^^^^
::

    doc = MyDoc(foo='42')  # or MyDoc({'foo': '42'})
    doc.bar = 42  # attribute style access because dot_notation=True
    doc.insert()

:meth:`~.document.BaseDocument.insert()` is a wrapper around
``pymongo.Collection().insert()`` and has the same return value (``_id``)
unless you explicitly set ``w=0`` ::

    doc.foo = 'new foo'  # this change is recorded
    del doc.bar  # this is recored as well
    doc.save()  # save only does partial updates, the query will be
    # 

:meth:`~.document.BaseDocument.save()` uses ``pymongo.Collection().update()``
with the changed data. The above will run ::

    update({'_id': doc['_id']}, {'$set': {'foo': 'new foo'}, '$unset': {'bar': 1}})

Querying
^^^^^^^^
::

    Doc.find({'bar': 42})
    Doc.find_one({'foo': 'new foo'})

Extensive Example
-----------------

See :doc:`example`

Advanced Features
-----------------

$addToSet
^^^^^^^^^

MongoDB ``$addToSet`` update modifier is very useful. nanomongo implements it.

:meth:`~.document.BaseDocument.addToSet()` will do the `add-to-field-if-doesnt-exist`
on your document instance and record the change to be applied later when
:meth:`~.document.BaseDocument.save()` is called.

::

    # lets expand our MyDoc
    class NewDoc(MyDoc):
        list_field = Field(list)
        dict_field = Field(dict)

    NewDoc.register(client=client, db='dbname')
    doc_id = NewDoc(list_field=[42], dict_field={'foo':[]}).insert()
    doc = NewDoc.find_one({'_id': doc_id})

    doc.addToSet('list_field', 1337)
    doc.addToSet('dict_field.foo', 'like a boss')
    doc.save()

Both of the above ``addToSet`` are applied to the ``NewDoc`` instance like MongoDB does it eg.

  - create list field with new value if it doesn't exist
  - add new value to list field if it's missing (append)
  - complain if it is not a list field

When save is called, query becomes: ::

    update({'$addToSet': {'list_field': {'$each': [1337]}},
                          'dict_field.foo': {'$each': ['like a boss']}})

Undefined fields or field type mismatch raises :class:`~.errors.ValidationError`.

QuerySpec check
^^^^^^^^^^^^^^^

:meth:`~.document.BaseDocument.find()` and :meth:`~.document.BaseDocument.find_one()`
has a simple check against queries that can not match, logging warnings. This is
an experimental feature at the moment and only does type checks as such:

``{'foo': 1}`` will log warnings if

- Document has no field named ``foo`` (field existence)
- ``foo`` field is not of type ``int`` (field data type)

or ``{'foo.bar': 1}`` will log warnings if

- ``foo`` field is not of type ``dict`` or ``list`` (dotted field type)

pymongo & motor
---------------

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
    doc.addToSet('bar', 1337)
    yield motor.Op(doc.save)

**Note** however that pymongo vs motor behaviour is not necessarily identical.
Asynchronous methods require ``tornado.ioloop.IOLoop``. For example,
:meth:`~.document.BaseDocument.register` runs ``ensure_index`` but the query will not be sent
to MongoDB until ``IOLoop.start()`` is called.

Contents
========

.. toctree::
   :titlesonly:

   field
   document
   util
   errors


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

