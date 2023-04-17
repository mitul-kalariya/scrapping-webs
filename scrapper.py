from crwnikkeinews import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()

for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"], "enable_selenium":"True"})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
