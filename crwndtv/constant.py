from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.ndtv.com/"
SITEMAP_URL = "https://www.ndtv.com/sitemap.xml"
PROXY_TIMEOUT = 5 # in seconds

LOGGER = logging.getLogger()
