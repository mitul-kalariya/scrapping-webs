"""constants"""

import logging
from datetime import datetime

TODAYS_DATE = datetime.today().date()
FORMATTED_DATE = TODAYS_DATE.strftime('%Y%m%d')
SITEMAP_URL = "https://mainichi.jp/shimen/tokyo/"
BASE_URL = 'https://mainichi.jp/'
LOGGER = logging.getLogger()
