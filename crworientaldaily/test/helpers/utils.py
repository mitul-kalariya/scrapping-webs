import requests
import json
from scrapy.http import Request, TextResponse


def online_response_from_url(url: str) -> TextResponse:
    """Call the external url and convert into scrapy Response

    Args:
        url (str): web address of article

    Returns:
        TextResponse: Converted Response object
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'}
    request = Request(url=url, headers=headers)

    raw_response = requests.get(url, headers=headers)

    response = TextResponse(url=url, request=request, headers=raw_response.headers,
                            body=raw_response.text, encoding='utf-8')
    return response


def get_article_content(file_name: str) -> dict:
    """Read json file and return as dict

    Args:
        file_name (str): JSON file path

    Returns:
        dict: JSON data
    """
    with open(file_name, 'r') as f:
        data = json.load(f)

    return data
