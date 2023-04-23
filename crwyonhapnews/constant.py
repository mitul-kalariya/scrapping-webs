"""constants"""

import logging


SITEMAP_URL = "https://en.yna.co.kr/news-sitemap.xml"
# In case when sitemap, RSS feed or archive is not available.
BASE_URL = "https://en.yna.co.kr/"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5 # in seconds