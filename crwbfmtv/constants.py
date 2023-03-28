from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
BASE_URL = "https://www.tagesschau.de"
SITEMAP_URL = "https://www.bfmtv.com/sitemap_index_arbo_contenu.xml"

LOGGER = logging.getLogger()
