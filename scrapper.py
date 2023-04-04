from crwmbnnewsonline import Crawler

# crawler = Crawler(query={"type": "link_feed"})
# links = crawler.crawl()

links = [   {
        "link": "https://www.mbn.co.kr/news/society/4917663",
        "test_data_path": "crwmbnnewsonline/test/data/test_article_1.json"
    },
    {
        "link": "https://www.mbn.co.kr/news/entertain/4917683",
        "test_data_path": "crwmbnnewsonline/test/data/test_article_2.json"
    },
    {
        "link": "https://www.mbn.co.kr/news/economy/4917667",
        "test_data_path": "crwmbnnewsonline/test/data/test_article_3.json"
    }
]
for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
