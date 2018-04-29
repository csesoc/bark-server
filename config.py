import os
from datetime import timedelta


class Config(object):
    DEBUG = False
    USE_FAKE_SERVICES = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../data/bark.db'
    UDB_URL = 'https://cgi.cse.unsw.edu.au/~csesoc/udb/'
    UDB_USER = 'udb'
    LDAP_HOST = 'ldap://ad.unsw.edu.au'
    EVENT_LEEWAY = timedelta(hours=1)

    # TODO: Add link to Android App Download
    ANDROID_URL = 'about:blank'


class Production(Config):
    PROPAGATE_EXCEPTIONS = True

    def __init__(self):
        self.SECRET_KEY = os.environ['SECRET_KEY']
        self.UDB_PASSWORD = os.environ['UDB_PASSWORD']


class Development(Config):
    DEBUG = True
    USE_FAKE_SERVICES = True
    SECRET_KEY = 'development-only'

    def __init__(self):
        super(Development, self).__init__()
        self.UDB_PASSWORD = os.environ.get('UDB_PASSWORD')
