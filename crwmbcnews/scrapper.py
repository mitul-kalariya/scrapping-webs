# TODO: Change the path below
from crwmbcnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
