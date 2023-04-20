from crwnikkeibusiness import Crawler

# Wrong Proxy Shared by Henry
# proxies = {
#     "proxyIp": "166.81.191.33",
#     "proxyPort": "4616",
#     "proxyUsername": "stt_proxy_user55",
#     "proxyPassword": "xw34$21dOoww_",
#     "proxyTimeout": 5
# }

# Proxy shared earlier
proxies = {
    "proxyIp": "104.239.117.168",
    "proxyPort": "3199",
    "proxyUsername": "daniel_morgan-57n47",
    "proxyPassword": "IgNyTnWKr5",
}

# Working Proxy created by us
# proxies = {
#     "proxyIp": "3.20.87.239",
#     "proxyPort": "3128",
#     "proxyUsername": "giqpeohf",
#     "proxyPassword": "entVdShG",
# }

try:
    crawler = Crawler(query={"type": "sitemap", "domain": "https://asia.nikkei.com/"}, proxies=proxies)
    links = crawler.crawl()
except Exception as e:
    print ("here----------------------------->", e)

# crawler = Crawler(query={"type": "link_feed"})
# links = crawler.crawl()

# links = [
#     {
#     "link": "https://www.nikkei.com/article/DGXZQOUC031X20T00C23A4000000/"
#     }
# ]

# print(f"Total {len(links)} found..")
# for link in links[:2]:
#     article = Crawler(query={"type": "article", "link": link["link"]})
#     data = article.crawl()
#     print("----------------------------------------------------")


# http://username:password@some_proxy_server:port
# stt_proxy_user55:xw34$21dOoww_@166.81.191.33:1616