from crwrepublictv import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()


links = [
    {
    "link": "https://bharat.republicworld.com/india-news/politics/rahul-gandhi-first-parliament-membership-was-lost-now-he-had-to-vacate-the-government-house"
    }
]
for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)

