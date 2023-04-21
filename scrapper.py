import json
import time
from crwtvchosun import Crawler

# crawler = Crawler(query={"type": "sitemap"})
# data = crawler.crawl()

# print(data)



links = [
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190135.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190126.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190126.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190134.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190134.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190133.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190133.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190132.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190132.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190131.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190131.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190130.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190130.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190129.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190129.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190128.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190128.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190127.html",
    },
    {
        "link": "http://news.tvchosun.com/site/data/html_dir/2023/04/21/2023042190127.html",
    },
]

for count, link in enumerate(links, start=1):
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    json_object = json.dumps(data, indent=4, ensure_ascii=False)
    with open(
        f"crwtvchosun/test/data/test_article_{count}.json",
        "w",
        encoding="utf-8",
    ) as f:
        f.write(json_object)
    print(data)
    time.sleep(5)
#     print("----------------------------------------------------")