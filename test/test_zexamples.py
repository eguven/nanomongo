from __future__ import unicode_literals
import six
import unittest

from examples.example import User, Entry

try:
    import pymongo
    PYMONGO_CLIENT = pymongo.MongoClient()
except:
    PYMONGO_CLIENT = False


class HelperFuncionsTestCase(unittest.TestCase):
    def setUp(self):
        User.get_collection().remove()
        Entry.get_collection().remove()

    def print_stuff(self, added, *args):
        if User == type(added):
            print('{0.name} joined, following: {0.following}'.format(added))
        elif Entry == type(added):
            print('{0.name} > "{1.title}", {1.categories}'.format(args[0], added))
        elif six.text_type == type(added):
            print('{1.name} commented: "{0}"'.format(added, args[0]))

    @unittest.skipUnless(PYMONGO_CLIENT, 'pymongo not installed or connection refused')
    def test_z_general_functionality(self):
        """Use case demo & test
        """
        print('\n')
        batman = User(name='Batman')
        batman.insert()
        batman.follow('crime', 'energy', 'arkham', 'gadgets')
        self.print_stuff(batman)
        selina = User(name='Selina Kyle', following=['gadgets'])
        selina.insert()
        selina.follow('billionaires')
        self.print_stuff(selina)
        news = User(name='Gotham News')
        news.insert()
        self.print_stuff(news)
        # Lets add some entries
        e1, e2, e3 = [
            news.add_entry('Arkham blocks city sewage system', categories=['arkham', 'lol']),
            news.add_entry('Rich people ball by this new chick in town', categories=['billionaires']),
            news.add_entry('Jetpack Belt released', categories=['gadgets'])
        ]
        for e in (e1, e2, e3):
            self.print_stuff(e, news)
        self.assertEqual(3, news.get_entries().count())
        self.assertTrue(1 == e1.get_followers().count() and
                        batman == e1.get_followers()[0])
        self.assertTrue(1 == e2.get_followers().count() and
                        selina == e2.get_followers()[0])
        e3followers = sorted(e3.get_followers(), key=lambda u: u['name'])
        self.assertTrue(2 == len(e3followers))
        self.assertEqual([batman, selina], e3followers)
        # some comments
        self.print_stuff(e1.add_comment('Those damn nutjobs!', batman), batman)
        self.print_stuff(e2.add_comment('Hawt and looking for a date to this', selina), selina)
        self.print_stuff(e3.add_comment('OMG WANT!', selina), selina)
        self.print_stuff(e3.add_comment('Aww Yea! Suck it Clark!', batman), batman)
        self.assertEqual(2, len([c for c in batman.get_comments()]))
        self.assertEqual(2, len([c for c in selina.get_comments()]))
        self.assertEqual(0, len([c for c in news.get_comments()]))
        for entry in batman.get_comments(with_entries=True, sort=[('_id', pymongo.DESCENDING)]):
            if entry.title.startswith('Arkham'):
                self.assertEqual(1, len(entry.comments))
            elif entry.title.startswith('Jetpack'):
                self.assertEqual(2, len(entry.comments))
            else:
                raise AssertionError('Extra entry received')
