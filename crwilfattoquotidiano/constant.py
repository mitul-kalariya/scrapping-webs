"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.ilfattoquotidiano.it/"
SITEMAP_URL = "https://www.ilfattoquotidiano.it/sitemap.xml"
PROXY_TIMEOUT = 5 # in seconds

LOGGER = logging.getLogger()