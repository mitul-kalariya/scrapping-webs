"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://tg24.sky.it/"
SITEMAP_URL = "https://tg24.sky.it/sitemap-index.xml"
PROXY_TIMEOUT = 5 # in seconds

LOGGER = logging.getLogger()