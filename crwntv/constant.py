from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
LINK_FEED_URL = "https://www.n-tv.de/news.xml"
BASE_URL = 'https://www.n-tv.de/'
LOGGER = logging.getLogger()