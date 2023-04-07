from crwrthknews import Crawler

crawler = Crawler(query={"type": "sitemap", "since": "2023-04-04", "until": "2023-04-04"})
# crawler = Crawler(query={"type": "article", "link": "https://news.rthk.hk/rthk/ch/video-gallery.htm?vid=1694993"})
data = crawler.crawl()

print(data)
