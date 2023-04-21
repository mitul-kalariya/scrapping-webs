import json
import time
from crwmbcnews import Crawler

crawler = Crawler(query={"type": "sitemap"})
links = crawler.crawl()
print(links)
for link in links[:5]:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
TEST_ARTICLES = [
    {"link": "https://imnews.imbc.com/news/2023/world/article/6475754_36133.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475753_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475750_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475749_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475748_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475747_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/society/article/6475746_36126.html"},
    {"link": "https://imnews.imbc.com/news/2023/politics/article/6475743_36119.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475742_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475741_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475740_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475739_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475738_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475737_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475736_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475735_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475734_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475733_36199.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nwdesk/article/6475732_36199.html"},
    {"link": "https://imnews.imbc.com/news/2023/society/article/6475731_36126.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nw930/article/6475473_36191.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475472_36161.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nw930/article/6475471_36191.html"},
    {"link": "https://imnews.imbc.com/news/2023/society/article/6475470_36126.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475468_36161.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475469_36161.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nw930/article/6475467_36191.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nw930/article/6475466_36191.html"},
    {"link": "https://imnews.imbc.com/news/2023/enter/article/6475465_36161.html"},
    {"link": "https://imnews.imbc.com/replay/2023/nw930/article/6475464_36191.html"},
]
# count = 1
# for link in TEST_ARTICLES:
#     article = Crawler(query={"type": "article", "link": link["link"]})
#     data = article.crawl()
#     json_object = json.dumps(data, indent=4, ensure_ascii=False)
#     with open(f"crwmbcnews/test/data/test_article_{count}.json", "w", encoding="utf-8") as f:
#         f.write(json_object)
#     print(data)
#     count+=1
#     time.sleep(15)
#     print("----------------------------------------------------")
