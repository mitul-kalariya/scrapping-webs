"""constants"""

from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.nippon.com/ja/"
SITEMAP_URL = "https://www.nippon.com/ja/articles.xml"
LOGGER = logging.getLogger()