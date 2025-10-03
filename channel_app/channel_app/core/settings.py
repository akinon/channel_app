import importlib
import os
from dotenv import load_dotenv
load_dotenv()

env_variables = os.environ

OMNITRON_CHANNEL_ID = os.getenv("OMNITRON_CHANNEL_ID")
OMNITRON_USER = os.getenv("OMNITRON_USERNAME")
OMNITRON_PASSWORD = os.getenv("OMNITRON_PASSWORD")
MAIN_APP_URL = os.getenv("MAIN_APP_URL")
OMNITRON_URL = f"https://{MAIN_APP_URL}/"
OMNITRON_CATALOG_ID = os.getenv("OMNITRON_CATALOG_ID")
CACHE_DATABASE_INDEX = os.getenv("CACHE_DATABASE_INDEX")
CACHE_HOST = os.getenv("CACHE_HOST")
CACHE_PORT = os.getenv("CACHE_PORT")
BROKER_HOST = os.getenv("BROKER_HOST")
BROKER_PORT = os.getenv("BROKER_PORT")
BROKER_DATABASE_INDEX = os.getenv("BROKER_DATABASE_INDEX")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
SENTRY_DSN = os.getenv("SENTRY_DSN")
DEFAULT_CONNECTION_POOL_COUNT = os.getenv("DEFAULT_CONNECTION_POOL_COUNT") or 10
DEFAULT_CONNECTION_POOL_MAX_SIZE = os.getenv("DEFAULT_CONNECTION_POOL_COUNT") or 10
DEFAULT_CONNECTION_POOL_RETRY = os.getenv("DEFAULT_CONNECTION_POOL_RETRY") or 0
REQUEST_LOG = os.getenv("REQUEST_LOG") or False

omnitron_module = importlib.import_module(os.getenv("OMNITRON_MODULE"))
OmnitronIntegration = omnitron_module.OmnitronIntegration

channel_module = importlib.import_module(os.getenv("CHANNEL_MODULE"))
ChannelIntegration = channel_module.ChannelIntegration
