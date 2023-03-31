from crwbild.main import Crawler

crawler = Crawler(query={"type": "sitemap", "since": "2023-03-31"})
data = crawler.crawl()

print(data)
