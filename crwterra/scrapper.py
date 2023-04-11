# TODO: Change the path below
from crwterra import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
