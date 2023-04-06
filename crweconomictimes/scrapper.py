# TODO: Change the path below
from crweconomictimes import Crawler

crawler = Crawler(query={"type": "link_feed"})
data = crawler.crawl()

print(data)