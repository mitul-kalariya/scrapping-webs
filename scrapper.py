from crwbbcnews import Crawler

crawler = Crawler(query={"type": "article", "link": "https://www.bbc.com/zhongwen/simp/chinese-news-65069676"})
data = crawler.crawl()

print(data)
