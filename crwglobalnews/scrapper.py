# TODO: Change the path below
from crwglobalnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
