import logging
from datetime import datetime
import pytz

korea_tz = pytz.timezone('Asia/Seoul')
now_korea = datetime.now(korea_tz)
now_korea_str = now_korea.strftime('%Y%m%d')
"""constants"""

#LINK_FEED_URL = "https://www.mbn.co.kr/google/sitemap/mbn_recent_index.xml"
LINK_FEED_URL = "https://www.mbn.co.kr/news/date/"
# In case when sitemap, RSS feed or archive is not available.
BASE_URL = "https://www.mbn.co.kr/news/"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5 # in seconds
CURRENT_DATE = now_korea_str
