# TODO: Change the path below
from crwndtv import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
