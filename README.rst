=========
nanomongo
=========

**nanomongo** is a minimal MongoDB Object-Document Mapper for Python.
It does not attempt to be a feature-complete ODM but if you like
using ``pymongo`` api with python dictionaries and often find yourself
writing validators and ``pymongo.Collection`` wrappers, nanomongo
might suit your needs.

nanomongo has full test coverage.

**Quick Links**: `Source (github) <https://github.com/eguven/nanomongo>`_ - `Documentation (rtd) <https://nanomongo.readthedocs.org/>`_ - `Packages (PyPi) <https://pypi.python.org/pypi/nanomongo/>`_

**Version 0.4**: Utility methods `dbref_field_getters <http://nanomongo.readthedocs.org/en/latest/index.html#dbref_field_getters>`_, `BaseDocument.get_dbref <http://nanomongo.readthedocs.org/en/latest/document.html#nanomongo.document.BaseDocument.get_dbref>`_
and Bugfix `Python23 text type compatibility <https://github.com/eguven/nanomongo/pull/14>`_

**Version 0.3**: nanomongo is now python2 compatible (with syntactic difference
when defining your Document, refer to Documentation)

.. image:: https://travis-ci.org/eguven/nanomongo.png
        :target: https://travis-ci.org/eguven/nanomongo

Features
--------

- single format ``Field`` definitions with type checking and a few common
  options such as ``required``, ``default``, ``auto_update``

- ``pymongo``-identical index definitions

- optional ``dot_notation``

- assignment and deletion (delta) tracking for ``'$set'`` and ``'$unset'``
  and atomic updates; you either insert or update

- ``'$addToSet'`` on ``Document``

- *upcoming* ``'$push'`` ``'$pull'`` funtionality

::

    # rough example
    import pymongo
    from nanomongo import Field, BaseDocument, Index

    client = pymongo.MongoClient()

    class MyDoc(BaseDocument, dot_notation=True, client=client, db='dbname'):
        foo = Field(str)
        bar = Field(int, required=False)

        __indexes__ = [
            Index('foo'),
            Index([('bar', 1), ('foo', -1)], unique=True),
        ]

    doc = MyDoc(foo='L33t')
    doc.bar = 42
    doc.insert()

    Doc.find_one({'foo': 'L33t'})


nanomongo is Python23 compatible and I intend to support both pymongo & motor
transparently under the hood.

Contributions and insight are welcome!

:Author: Eren Güven (GitHub_, Twitter_)
:License: Apache Software License

.. _GitHub: https://github.com/eguven
.. _Twitter: https://twitter.com/cyberfart
