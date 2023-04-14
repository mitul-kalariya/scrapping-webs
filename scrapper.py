from crwglobalnews import Crawler

crawler = Crawler(query={"type": "link_feed"})
links = crawler.crawl()
print(links)
for link in links[:2]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
