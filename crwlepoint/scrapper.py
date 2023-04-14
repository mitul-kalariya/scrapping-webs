from crwlepoint import Crawler

crawler = Crawler(query={"type": "link_feed"})
data = crawler.crawl()

print(data)
