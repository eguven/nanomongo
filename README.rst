=========
nanomongo
=========

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python.
It does not attempt to be a feature-complete ODM but if you like
using ``pymongo`` api with python dictionaries and often find yourself
writing validators and ``pymongo.Collection`` wrappers, nanomongo
might suit your needs.

nanomongo has full test coverage.

**Quick Links**: `Source (github) <https://github.com/eguven/nanomongo>`_ - `Documentation (rtd) <https://nanomongo.readthedocs.org/>`_ - `Packages (PyPi) <https://pypi.python.org/pypi/nanomongo/>`_ - `Changelog <https://github.com/eguven/nanomongo/blob/master/CHANGELOG.md>`_

.. image:: https://travis-ci.org/eguven/nanomongo.png
        :target: https://travis-ci.org/eguven/nanomongo

Features
--------

- typed ``Field`` definitions with validators and a few common options such as ``required``, ``default``, ``auto_update``
- ``IndexModel`` definitions within Document classes that are automatically created 
- optional ``dot_notation``
- assignment and deletion (delta) tracking for ``'$set'`` and ``'$unset'``
  and atomic updates; you either insert or update
- ``'$addToSet'`` on ``Document``

::

    # simple example
    import pymongo
    from nanomongo import Field, BaseDocument

    client = pymongo.MongoClient()

    class MyDoc(BaseDocument, dot_notation=True, client=client, db='dbname'):
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            pymongo.IndexModel('foo'),
            pymongo.IndexModel([('bar', 1), ('foo', -1)], unique=True),
        ]

    doc = MyDoc(foo='L33t')
    doc.bar = 42
    doc.insert()

    Doc.find_one({'foo': 'L33t'})


nanomongo is Python23 compatible and I intend to support both pymongo & motor
transparently under the hood.

Contributions and insight are welcome!

:Author: Eren Güven (GitHub_, Twitter_)
:License: `Apache License 2.0 <https://github.com/eguven/nanomongo/blob/master/LICENSE>`_

.. _GitHub: https://github.com/eguven
.. _Twitter: https://twitter.com/cyberfart
