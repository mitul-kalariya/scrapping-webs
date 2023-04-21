from datetime import datetime
import logging

TODAYS_DATE = datetime.today().date()
LOGGER = logging.getLogger()
BASE_URL = "https://globalnews.ca/"
LINK_FEED_URL = "http://globalnews.ca/news-sitemap.xml"

PROXY_TIMEOUT = 5 # in seconds

CATEGORIES_URLS = ["https://globalnews.ca/world/",
                   "https://globalnews.ca/canada/",
                   "https://globalnews.ca/national/",
                   "https://globalnews.ca/money/",
                   "https://globalnews.ca/politics/",
                   "https://globalnews.ca/health/",
                   "https://globalnews.ca/entertainment/",
                   "https://globalnews.ca/lifestyle/",
                   "https://globalnews.ca/sports/",
                   "https://globalnews.ca/tech/",
                   "https://globalnews.ca/environment/",
                   "https://globalnews.ca/us-news/",
                   "https://globalnews.ca/perspectives/"
                   ]