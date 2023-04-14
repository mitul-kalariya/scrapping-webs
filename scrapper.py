from crwam730 import Crawler

proxies = {
    "proxyIp": "168.81.229.17",
    "proxyPort": "3199",
    "proxyUsername": "",
    "proxyPassword": "IgNyTnWKr5"
}

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()

for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")