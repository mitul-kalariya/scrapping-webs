from crwntv import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)