"""constants"""
from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.ilfattoquotidiano.it/"
SITEMAP_URL = "https://www.ilfattoquotidiano.it/in-edicola/edizione/"

LOGGER = logging.getLogger()