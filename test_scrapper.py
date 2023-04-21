from crwskytg24 import Crawler

# # Wrong Proxy Shared by Henry
# proxies = {
#     "proxyIp": "166.81.191.33",
#     "proxyPort": "4616",
#     "proxyUsername": "stt_proxy_user55",
#     "proxyPassword": "xw34$21dOoww_",
#     "proxyTimeout": 5,
# }

# Proxy shared earlier
# proxies = {
#     "proxyIp": "104.239.117.168",
#     "proxyPort": "3199",
#     "proxyUsername": "daniel_morgan-57n47",
#     "proxyPassword": "IgNyTnWKr5",
# }

# Working Proxy created by us
# proxies = {
#     "proxyIp": "3.20.87.239",
#     "proxyPort": "3128",
#     "proxyUsername": "testuser",
#     "proxyPassword": "testpass",
#     "proxyTimeout": 5,
# }
proxies = {
    "proxyIp": "3.20.87.239",
    "proxyPort": "3128",
    "proxyUsername": "giqpeohf",
    "proxyPassword": "entVdShG",
}

try:
    crawler = Crawler(
        query={"type": "sitemap", "domain": "https://tg24.sky.it/"}, proxies=proxies
    )
    links = crawler.crawl()
    # print("\n\n\n\n Done \n ------------------")
except Exception as e:
    print("\n\n\n\n here \n ------------------ ", e)
