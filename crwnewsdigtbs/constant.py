"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
SITEMAP_URL = "https://newsdig.tbs.co.jp/sitemap.xml/"
# In case when sitemap, RSS feed or archive is not available.
BASE_URL = "https://newsdig.tbs.co.jp/articles/mro/405798"

LOGGER = logging.getLogger()
