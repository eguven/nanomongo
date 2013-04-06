=========
nanomongo
=========

**very** early stage and in development::


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

nanomongo is written for Python3 and I intend to support both pymongo & motor
under the hood.