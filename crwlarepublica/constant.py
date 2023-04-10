"""constants"""

from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()

BASE_URL = "https://www.repubblica.it/"
SITEMAP_URL = "https://www.repubblica.it/sitemap-n.xml"

LOGGER = logging.getLogger()