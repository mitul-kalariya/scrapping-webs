"""constants"""

from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.tagesschau.de"
ARCHIVE_URL = "https://www.tagesschau.de/archiv/"
LOGGER = logging.getLogger()
