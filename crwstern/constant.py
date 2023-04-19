from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.stern.de/"
SITEMAP_URL = "https://www.stern.de/archiv/"
PROXY_TIMEOUT = 5

LOGGER = logging.getLogger()