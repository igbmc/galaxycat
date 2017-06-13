# coding=utf-8

import logging
import os

from flask.config import Config


__all__ = ['config']

logger = logging.getLogger(__name__)


class DefaultConfig:
    DEBUG = False
    TESTING = False

    # Extensions and external librairies config
    BABEL_TRANSLATION_DIRECTORIES = '../translations'
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'UTC+1'

    # App config
    MONGODB_HOST = 'localhost'
    MONGODB_PORT = 27017
    MONGODB_DB = 'galaxycat'

    # Logging standard configuration : override default Flask logging
    # https://docs.python.org/2/library/logging.config.html#logging.config.dictConfig
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,  # Removes existing loggers
        'formatters': {
            'simple': {
                'format': '[%(asctime)s-%(levelname)8s][%(name)-10s]%(message)s',
                'datefmt': '%d/%m/%y %H:%M:%S'
            },
            'short': {
                'format': '[BIS %(asctime)s%(msecs)d-%(levelname).1s][%(name)-9s]%(message)s',
                'datefmt': '%M%S'  # miliseconds will be added by the format string
            },
            'long': {
                'format': '[%(asctime)s:%(levelname)s][%(name)-10s]%(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'stream': 'ext://sys.stderr'
            }
        },
        'loggers': {
            'harpgest': {
                'handlers': ['console'],
                'level': logging.INFO,
            }
        }
    }


config = Config(os.getcwd())
config.from_object(DefaultConfig)
config.from_pyfile(os.path.join(os.getcwd(), 'app.cfg'), silent=True)
