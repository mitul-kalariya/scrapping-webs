"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://tg24.sky.it/"
LINK_FEED = "https://tg24.sky.it/ultime-notizie"
PROXY_TIMEOUT = 5 # in seconds

LOGGER = logging.getLogger()