import logging

"""constants"""

LINK_FEED_URL = "https://www.mbn.co.kr/google/sitemap/mbn_recent_index.xml"
# In case when sitemap, RSS feed or archive is not available.
BASE_URL = "https://www.mbn.co.kr/news/"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5 # in seconds
