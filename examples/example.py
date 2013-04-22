from datetime import datetime

import bson
import pymongo

from nanomongo import Index, Field, BaseDocument


class User(BaseDocument, dot_notation=True):
    """A user has a name, a list of categories he follows and a dictionary
    for preferences.

    We index on :attr:`~User.name` field and on
    :attr:`~User.following` + :attr:`preferences.notifications` (compound),
    think of listing followers of a category who have notifications enabled.
    """
    name = Field(str)
    following = Field(list, default=[])
    preferences = Field(dict, default={'notifications': True})

    __indexes__ = [
        Index('name'),
        Index([('following', pymongo.ASCENDING),
               ('preferences.notifications', pymongo.ASCENDING)])
    ]

    def add_entry(self, title, categories=None):
        """Add an entry with title and categories and ``user=self._id``"""
        assert (title and isinstance(title, str)), 'title not str or empty'
        e = Entry(user=self._id, title=title)
        if categories:
            assert isinstance(categories, list), 'categories not a list'
            for cat in categories:
                assert (cat and isinstance(cat, str)), 'categories element not str or empty'
            e.categories = categories
        e.insert()
        return e

    def follow(self, *categories):
        """Start following a category (add it to :attr:`~self.categories`)"""
        assert categories, 'categories expected'
        for category in categories:
            assert (category and isinstance(category, str)), 'category not str or emtpy'
            self.addToSet('following', category)
        self.save()

    def get_entries(self, **kwargs):
        """Get entries (well cursor for them) of this User, extra kwargs
        (such as limit) are passed to :class:`~pymongo.Collection().find()`
        """
        cursor = Entry.find({'user': self._id}, **kwargs)
        # hint not necessary here, just demonstration
        cursor.hint([('user', pymongo.ASCENDING), ('_id', pymongo.DESCENDING)])
        return cursor

    def get_comments(self, with_entries=False, **kwargs):
        """Get comments of this User, extra kwargs
        (such as limit) are passed to :class:`~pymongo.Collection().find()`
        of :class:`Entry`. Default gets just the comments, ``with_entries=True``
        to get entries as well. Returns generator/cursor
        """
        cursor = Entry.find({'comments.author': self.name}, **kwargs)
        if with_entries:
            return cursor
        for entry in cursor:
            for comment in entry.comments:
                if self.name == comment['author']:
                    yield comment


class Entry(BaseDocument, dot_notation=True):
    """An entry that a :class:`~User` posts; has a title, a user field
    pointing to a User _id, a list of categories that the entry belongs
    and a list for comments.

    We index on categories, 'comments.author' + 'comment.created'
    so we can lookup comments by author and
    'user' + '_id' so we can chronologically sort entries by user
    """
    user = Field(bson.objectid.ObjectId)
    title = Field(str)
    categories = Field(list, default=[])
    comments = Field(list, default=[])

    __indexes__ = [
        Index([('user', pymongo.ASCENDING), ('_id', pymongo.DESCENDING)]),
        Index('categories'),
        Index([('comments.author', pymongo.ASCENDING), ('comments.created', pymongo.DESCENDING)]),
    ]

    def add_comment(self, text, author):
        """Add a comment to this Entry"""
        assert (text and isinstance(text, str)), 'text not str or empty'
        assert (author and isinstance(author, User)), 'second argument not an instance of User'
        doc = {'text': text, 'author': author.name, 'created': datetime.utcnow()}
        # TODO: push is more appropriate in this situation, add when implemented
        self.addToSet('comments', doc)
        # we could have also done self.comments = self.comments + [doc]
        self.save()
        return text

    def get_followers(self):
        """Return a cursor for Users who follow the categories that this Entry has
        """
        return User.find({'following': {'$in': self.categories}})

client = pymongo.MongoClient()
User.register(client=client, db='nanotestdb')
Entry.register(client=client, db='nanotestdb')
