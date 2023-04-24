"""constants"""
from datetime import datetime
import logging

PROXY_TIMEOUT = 5  # in seconds
TODAYS_DATE = datetime.today().date()
LOGGER = logging.getLogger()
BASE_URL = "https://yonhapnewstv.co.kr/"
LINK_FEED_URL = "https://www.yonhapnewstv.co.kr/news/getNewsList"
