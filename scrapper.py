from crwntv import Crawler

crawler = Crawler(query={"type": "link_feed"})
links = crawler.crawl()

for link in links[:10]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
