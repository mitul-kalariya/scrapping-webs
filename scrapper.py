from crweconomictimes import Crawler

crawler = Crawler(query={"type": "sitemap", "since":"2022-03-26", "until": "2022-03-26"})
data = crawler.crawl()

print(data)
