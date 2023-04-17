"""constants"""

import logging
from datetime import datetime

TODAYS_DATE = datetime.today().date()
SITEMAP_URL = "https://www.bbc.com/zhongwen/simp.json"
BASE_URL = "https://www.bbc.com/zhongwen/simp"
LOGGER = logging.getLogger()