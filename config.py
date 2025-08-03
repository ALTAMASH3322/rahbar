import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hello'

    # Database configuration
    MYSQL_USER = 'alta'
    MYSQL_PASSWORD = 'hello'
    MYSQL_HOST = '194.195.87.118'
    #MYSQL_USER = 'root'
    #MYSQL_PASSWORD = ''
    #MYSQL_HOST = '127.0.0.1'
    MYSQL_DB = 'rahbar'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login configuration
    LOGIN_DISABLED = False

    #hello