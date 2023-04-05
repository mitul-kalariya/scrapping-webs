from crwnippon import Crawler

crawler = Crawler(query={"type": "article", "link": "https://www.nippon.com/ja/images/i00066/"})
data = crawler.crawl()

print(data)
