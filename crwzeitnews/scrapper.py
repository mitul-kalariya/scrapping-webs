# TODO: Change the path below
from crwzeitnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
