from crwzdfnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

for link in data[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
