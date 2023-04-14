# TODO: Change the path below
from crwstern import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
