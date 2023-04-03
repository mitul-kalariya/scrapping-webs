from crwheadlinedaily import Crawler

crawler = Crawler(
    query={
        "type": "article",
        "link": "https://hd.stheadline.com/news/daily/spt/1022347/%E6%97%A5%E5%A0%B1-%E9%AB%94%E8%82%B2-%E9%9C%B8%E6%B0%A3%E5%A4%96%E9%9C%B2"
    }
)

data = crawler.crawl()
print(data)
