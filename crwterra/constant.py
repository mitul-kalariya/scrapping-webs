from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.terra.com.br/"
SITEMAP_URL = "https://www.terra.com.br/sitemap.xml"
PROXY_TIMEOUT = 5

LOGGER = logging.getLogger()
