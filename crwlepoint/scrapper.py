# TODO: Change the path below
from crwlepoint import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
