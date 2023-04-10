# TODO: Change the path below
from crwrainews import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
