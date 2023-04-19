"""constants"""

from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.metropoles.com/"
SITEMAP_URL = "https://www.metropoles.com/sitemap.xml"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5  # in seconds
