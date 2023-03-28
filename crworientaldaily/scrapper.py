#TODO: Change the path below
from crworientaldaily import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
