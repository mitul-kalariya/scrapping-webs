"""constants"""

import logging
from datetime import datetime

TODAYS_DATE = datetime.today().date()
SITEMAP_URL = "https://noticias.r7.com/indice_noticias_sitemaps.xml"
BASE_URL = "https://noticias.r7.com/"
LOGGER = logging.getLogger()
PROXY_TIMEOUT = 5  # in seconds
