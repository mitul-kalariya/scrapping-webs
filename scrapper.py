from crwbild.main import Crawler

crawler = Crawler(query={"type": "sitemap"})
data = crawler.crawl()

links = [
    {
        "url": "https://www.bild.de/bild-plus/regional/hamburg/hamburg-aktuell/techniker-von-kunde-eingesperrt-weil-internet-nicht-lief-83460238.bild.html",
        "test_data_path": "crwbild/test/data/test_article_1.json"
    },
    {
        "url": "https://www.bild.de/regional/ruhrgebiet/ruhrgebiet-aktuell/umbenennung-nach-116-jahren-uni-muenster-jagt-kaiser-wilhelm-vom-hof-83461618.bild.html",
        "test_data_path": "crwbild/test/data/test_article_2.json"
    },
    {
        "url": "https://www.bild.de/sport/mehr-sport/handball/wetzlar-trainer-horvat-weg-das-steckt-hinter-der-vertrauensbruch-rauswurf-83454824.bild.html",
        "test_data_path": "crwbild/test/data/test_article_3.json"
    }
]


# crawler = Crawler(query={"type": "sitemap"})
# links = crawler.crawl()

for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["url"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
