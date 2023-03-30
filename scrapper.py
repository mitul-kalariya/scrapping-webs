import json
from crw20minutesonline import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()
counter = 0
links = links[:5]
for link in links:
    crawler = Crawler(query={"type": "article", "link": link['link']})
    article = crawler.crawl()
    with open(f"article_{counter}.json", "w") as file:
        file.write(json.dumps(article, indent=4))
    counter += 1