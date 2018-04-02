import pymongo

PYMONGO_CLIENT = pymongo.MongoClient(serverSelectionTimeoutMS=500)

try:
    PYMONGO_CLIENT.admin.command('ismaster')
except pymongo.errors.ServerSelectionTimeoutError:
    PYMONGO_CLIENT = None

TEST_DBNAME = 'nanotestdb'
