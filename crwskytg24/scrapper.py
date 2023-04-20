# TODO: Change the path below
from crwskytg24 import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
