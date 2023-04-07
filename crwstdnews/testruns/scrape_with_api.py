import requests
import json

url = "https://std.stheadline.com/realtime/get_more_instant_news"

payload = "page=1"
headers = {
  'authority': 'std.stheadline.com',
  'accept': 'application/json, text/javascript, */*; q=0.01',
  'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
  'dnt': '1',
  'origin': 'https://std.stheadline.com',
  'referer': 'https://std.stheadline.com/realtime/%E5%8D%B3%E6%99%82',
  'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Linux"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
  'x-requested-with': 'XMLHttpRequest',
}

response_page1 = requests.request("POST", url, headers=headers, data=payload)
response_page2 = requests.request("POST", url, headers=headers, data="page=2")
with open("information.json", "w") as f:
    f.write(json.dumps(response_page1.json()))
    f.write(json.dumps(response_page2.json()))

print(response_page1)
print(response_page2)