import os

class Config:
    SECRET_KEY = os.environ['SECRET_KEY']

    # Database
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'chocomap')
    MYSQL_CURSORCLASS = 'DictCursor'

    # Localization
    BABEL_DEFAULT_LOCALE = 'cs'
    BABEL_TRANSLATION_DIRECTORIES = 'app/translations'
