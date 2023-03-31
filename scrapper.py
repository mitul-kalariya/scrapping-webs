from crwntv import Crawler

crawler = Crawler(query={"type": "article", "link": "https://www.n-tv.de/leute/Gedeon-Burkhard-Schauspieler-lebt-in-Berlin-mit-drei-Frauen-zusammen-article24020571.html"})
data = crawler.crawl()

print(data)
