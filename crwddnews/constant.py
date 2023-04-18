from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://ddnews.gov.in/hi"
ARCHIVE_URL = "https://ddnews.gov.in/hi/about/news-archive"
PROXY_TIMEOUT = 5

LOGGER = logging.getLogger()
