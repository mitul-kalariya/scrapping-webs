import json
from datetime import datetime
from json import JSONDecodeError

from scrapy.http import Response
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def check_cmd_args(self, start_date: str, end_date: str) -> None:
    """
       Checks the command-line arguments and sets the appropriate parameters for the TimesNow spider.
    Args:
        self (TimesNow): The TimesNow spider instance.
        start_date (str): The start date for the sitemap spider in the format YYYY-MM-DD.
        end_date (str): The end date for the sitemap spider in the format YYYY-MM-DD.
    Raises:
        ValueError: If the type is not "articles" or "sitemap".
        ValueError: If the type is "sitemap" and either start_date or end_date is missing.
        ValueError: If the type is "sitemap" and the time range is more than 30 days.
        ValueError: If the type is "articles" and the URL is missing.
    Returns:
        None.
       Note:
           This function assumes that the class instance variable `start_urls` is already initialized as an empty list.
       """
    initial_url = "https://www.cp24.com/sitemap.xml"
    if self.type == "sitemap" and self.end_date is not None and self.start_date is not None:
        self.start_date = datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if (self.end_date - self.start_date).days > 30:
            raise ValueError("Enter start_date and end_date for maximum 30 days.")
        else:
            self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.start_date is None and self.end_date is None:
        today_time = datetime.today().strftime("%Y-%m-%d")
        self.today_date = datetime.strptime(today_time, '%Y-%m-%d')
        self.start_urls.append(initial_url)

    elif self.type == "sitemap" and self.end_date is not None or self.start_date is not None:
        raise ValueError("to use type sitemap give only type sitemap or with start date and end date")

    elif self.type == "article" and self.url is not None:
        self.start_urls.append(self.url)

    elif self.type == "article" and self.url is None:
        raise ValueError("type articles must be used with url")
    else:
        raise ValueError("type should be articles or sitemap")


def get_article_data(self, response: Response) -> dict:
    """
         Extracts relevant data from the response of the given URL
         :param self: Spider instance
         :param response: The response object obtained from a HTTP request to the URL
         :return: A dictionary containing relevant article data.
         """
    mapper = {"CA": "Canada", "en": "English"}
    article_data = {}
    article_data["title"] = response.css('h1.articleHeadline::text').get()
    article_data["img_url"] = response.css('div.article div.image img::attr(src)').get()
    article_data["img_caption"] = response.css('div.article div.image p::text').get()
    article_body_img = response.css('div.articleBody p img::attr(src)').getall()
    article_data["author_url"] = response.css('div.prof a::attr("href")').get()
    article_data["text"] = " ".join(response.css('div.articleBody > p::text').getall())
    section_meta = response.xpath('//meta[@property="article:section"]')
    article_data["section_content"] = section_meta.xpath('@content').get()
    selector = response.xpath('//script[@type="application/ld+json"]/text()').getall()

    language = response.css("html::attr(lang)").get()
    #  if language not found static value will be provided
    if not language:
        language = mapper.get("en")
    article_data["language"] = mapper.get(language)
    article_data["country"] = mapper.get("CA")

    json_ld_blocks = []
    for sec in selector:
        try:
            json_ld_blocks.append(json.loads(sec))
        except JSONDecodeError as e:
            self.logger.error(f'>>>>>  {e}')
            new_str = sec.replace("],", "")
            json_ld_blocks.append(json.loads(new_str))
    try:
        article_data["json_ld_blocks"] = json_ld_blocks
    except Exception as e:
        self.logger.exception(f"Error{e}")

    article_data["article_img"] = [{"link": article, "caption": None} for article in article_body_img]

    string = selector[0]
    try:
        json_data = json.loads(string)

    except JSONDecodeError as e:
        self.logger.error(f'>>>>>>  {e}')
        new_str = string.replace("],", "")
        json_data = json.loads(new_str)
    article_data["json_data"] = json_data

    modified_date = json_data.get("modified_date")

    article_data["modified_date"] = modified_date
    article_data["video_url"] = get_video(self, response.url)
    return article_data


def get_video(self, url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    service = Service(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    try:
        textarea = driver.find_element(By.XPATH, '//*[@id="jw-settings-submenu-sharing"]/div/div[2]/textarea')
        value = textarea.get_attribute("value")

        iframe_string = value
        soup = BeautifulSoup(iframe_string, 'html.parser')
        video_url = soup.iframe.get("src")
        element = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.XPATH, '//video[@class="jw-video jw-reset"]'))
        )
    except Exception as e:
        self.logger.exception(f"Error in {get_video.__name__} -> {e}")
    else:
        return video_url


def set_article_dict(response: Response, article_data: dict) -> dict:
    """
      Takes in a `Response` object and a dictionary containing article data, and returns a dictionary
      containing the article information in a standardized format.
      Args:
          response (requests.Response): A `Response` object containing the raw HTTP response data.
          article_data (dict): A dictionary containing the extracted article data.
      Returns:
          dict: A dictionary containing the article information in a standardized format. The
          dictionary contains three main sections: `raw_response`, `parsed_json`, and `parsed_data`.
          The `raw_response` section contains the raw response data from the HTTP request, while
          the `parsed_json` section contains the parsed JSON-LD or json data extracted from the article.
          The `parsed_data` section contains the article information extracted from the raw HTML data.
      """
    article = {
        'raw_response': {
            "content_type": response.headers.get("Content-Type").decode("utf-8"),
            "content": response.text,
        },
        "parsed_json": {
            "main": article_data.get("json_ld_blocks")
        },
        "parsed_data": {
            "language": article_data["language"],
            "country": article_data["country"],
            "author": [{'@type': article_data.get("json_data")['author'][0]["@type"]
            if article_data.get("json_data").get("author") else None,
                        'name': article_data.get("json_data")['author'][0]['name'] if article_data.get("json_data").get(
                            "author") else None,
                        'url': article_data.get("author_url")}],
            "description": [article_data.get("json_data")['description']],
            "published_at": [article_data.get("json_data")['datePublished']],
            "publisher": [{'@id': article_data.get("json_ld_blocks")[1]['url'],
                           '@type': article_data.get("json_data")['publisher']['@type'],
                           'name': article_data.get("json_data")['publisher']['name'],
                           'logo': {'@type': article_data.get("json_data")['publisher']['logo']['@type'],
                                    'url': article_data.get("json_data")['publisher']['logo']['url'],
                                    'width': {'@type': "Distance",
                                              "name": str(article_data.get("json_data")
                                                          ['publisher']['logo']['width']) + " Px"},
                                    'height': {'@type': "Distance",
                                               'name': str(article_data.get("json_data")
                                                           ['publisher']['logo']['height']) + " Px"}}}],
            "text": [article_data.get("text")],
            "thumbnail_image": [article_data.get("img_url")],  # need to look it
            "title": [article_data.get("title")],
            "images": [{'link': article_data.get("img_url"),
                        'caption': article_data.get("img_url")}] + article_data.get("article_img"),
            "section": "".join(article_data.get("section_content")).split(","),
            "embed_video_link": [
                article_data.get("video_url")
            ]
        }
    }

    return article
