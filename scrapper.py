from crwhuffpost import Crawler

crawler = Crawler(query={"type": "article", "link": "https://www.huffingtonpost.fr/international/article/lula-veut-que-l-ukraine-renonce-a-la-crimee-pour-mettre-fin-a-la-guerre_216273.html"})
data = crawler.crawl()

print(data)
