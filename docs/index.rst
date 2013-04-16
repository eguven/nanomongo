.. nanomongo documentation master file, created by
   sphinx-quickstart on Tue Apr 16 16:21:17 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nanomongo's documentation!
=====================================

*this documentation is incomplete and the project is in alpha stage*

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python.
It does not attempt to be a fully-featured ODM; but if you like
using ``pymongo`` api with python ``dict`` and often find yourself
writing validators and ``pymongo.Collection`` wrappers etc, nanomongo
might suit your needs.

::

    import pymongo
    from nanomongo import Index, Field, BaseDocument

    client = pymongo.MongoClient()

    class MyDoc(BaseDocument, dot_notation=True, client=client, db='dbname'):
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            Index('foo'),
            Index([('bar', 1), ('foo', -1)], unique=True),
        ]

    doc = MyDoc(foo='42')  # or MyDoc({'foo': '42'})
    doc.bar = 42  # attribute style access because dot_notation=True
    doc.insert()
    doc.foo = 'new foo'  # this change is recorded
    del doc.bar  # this is recored as well
    doc.save()  # save only does partial updates, the query will be
    # update({'_id': doc['_id'], {'$set': {'foo': 'new foo'}, '$unset': {'bar': 1}}})

    Doc.find_one({'foo': 'new foo'})


Contents:

.. toctree::
   :titlesonly:

   field
   document


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

