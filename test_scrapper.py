from crwam730 import Crawler


proxies = {
    "proxyIp": "168.81.229.17",
    "proxyPort": "3199",
    "proxyUsername": "",
    "proxyPassword": "IgNyTnWKr5"
}


# crawler = Crawler(query={"type": "sitemap", "since": "2023-04-10", "until":"2023-04-13"})
# links = crawler.crawl()
# print(links)


# , "since": "2023-04-04", "until":"2023-04-04"

# crawler = Crawler(query={"type": "link_feed"})
# links = crawler.crawl()



# links = [
#     {
#     "link": "https://news.rthk.hk/rthk/ch/component/k2/1694886-20230404.htm?archive_date=2023-04-04"
#     }
# ]

# print(f"Total {len(links)} found..")

links = [
    {
    "link" : "https://www.am730.com.hk/本地/內地女捲冒廉電騙案-來港開戶串謀洗黑錢判囚1年/371169"
    },
    # {
    # "link" : "https://www.am730.com.hk/娛樂/薛影儀處女單曲破100萬views-一加一等於阿儀-打入k歌榜/371245"
    # }
]



for link in links:
    article = Crawler(query={"type": "article", "link": link["link"]})
    data = article.crawl()
    print(data)
    print("----------------------------------------------------")
