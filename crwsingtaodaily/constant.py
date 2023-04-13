"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
LOGGER = logging.getLogger()
BASE_URL = "https://std.stheadline.com/"
LINK_FEED_URL = "https://std.stheadline.com/realtime/get_more_instant_news"