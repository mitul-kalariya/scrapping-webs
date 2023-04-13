from crwheadlinedaily import Crawler

proxies = {
    "proxyIp": "168.81.229.17",
    "proxyPort": "3199",
    "proxyUsername": "",
    "proxyPassword": "IgNyTnWKr5"
}


crawler = Crawler(query={"type": "link_feed"})
links = crawler.crawl()
print(links)
# links = [
#     {
#     "link": "https://hd.stheadline.com/news/daily/hk/1022299/%E6%97%A5%E5%A0%B1-%E6%B8%AF%E8%81%9E-%E8%B6%85%E6%8A%B5%E5%83%B9%E5%90%B8%E5%AE%A2-%E6%94%B6%E9%8C%A2%E5%8D%B3%E5%A4%B1%E8%81%AF-%E9%A8%99%E5%BE%92%E5%90%BC%E9%99%A4%E7%BD%A9%E5%9F%B7%E6%A8%A3%E7%86%B1%E6%BD%AE-%E5%81%87%E7%B6%B2%E5%80%9F%E7%BE%8E%E5%AE%B9%E6%A9%9F%E6%8E%A0%E6%B0%B4"
#     }
# ]
for link in links[:2]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")

