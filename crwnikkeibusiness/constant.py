"""constants"""

import logging
from datetime import datetime

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://asia.nikkei.com/"
SITEMAP_URL = "https://www.hk01.com/sitemap.xml"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5