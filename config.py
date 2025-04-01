import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hello'

    # Database configuration
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'Spidey@321654'
    MYSQL_HOST = '139.59.3.48'
    MYSQL_DB = 'rahbar'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login configuration
    LOGIN_DISABLED = False