"""constants"""

import logging
from datetime import datetime

TODAYS_DATE = datetime.today().date()
FORMATTED_DATE = TODAYS_DATE.strftime('%Y%m%d')
SITEMAP_URL = "https://jtbc.co.kr/sitemap"
BASE_URL = 'https://jtbc.co.kr/'
LOGGER = logging.getLogger()