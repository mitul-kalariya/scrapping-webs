from crwtvanouvelles import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

print(data)
