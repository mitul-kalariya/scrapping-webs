"""Spider to scrap HuffingtonPost france news website"""

import logging
import scrapy
import json
import itertools
from datetime import date, timedelta, datetime
from scrapy.crawler import CrawlerProcess
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings


# Setting the threshold of logger to DEBUG
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] %(levelname)s:   %(message)s",
    filename="logs.log",
    filemode="a",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# Creating an object
logger = logging.getLogger()


class HuffPostSpider(scrapy.Spider):
    """Spider class to scrap sitemap and articles of huffington Post site"""

    name = "huff_post"
    namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def __init__(self, category=None, start_date=None, end_date=None, *args, **kwargs):
        """init method to take date, category and validating it"""

        super(HuffPostSpider, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.date_range_lst = []
        self.scrape_start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )
        self.scrape_end_date = (
            datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        )
        self.category = category

        if self.category == "sitemap":
            self.start_urls.append("https://www.huffingtonpost.fr/sitemaps/index.xml")
        elif self.category == "articles":
            self.start_urls.append("https://www.huffingtonpost.fr/")
        else:
            raise ValueError(
                "Invalid category argument. Must be 'sitemap' or 'articles'."
            )

        if self.scrape_end_date and self.scrape_start_date > self.scrape_end_date:
            raise ValueError("Please enter valid date range.")

        if self.scrape_start_date and self.category == "articles":
            for single_date in self.date_range(
                self.scrape_start_date, self.scrape_end_date
            ):
                self.date_range_lst.append(single_date)

    def date_range(self, start_date, end_date=None):
        """
        return range of all date between given date
        if not end_date then take start_date as end date
        """
        if not end_date:
            end_date = start_date
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)

    def parse(self, response):
        """
        differentiate sitemap and articles and redirect its callback to different parser
        """
        self.logger.info("Parse function called on %s", response.url)
        if "index.xml" in response.url:
            if self.scrape_start_date:
                for single_date in self.date_range(
                    self.scrape_start_date, self.scrape_end_date
                ):
                    self.logger.debug("Parse function called on %s", response.url)
                    print(
                        "Scraping articles from date: {}".format(self.scrape_start_date)
                    )
                    yield scrapy.Request(
                        f"https://www.huffingtonpost.fr/sitemaps/articles/{single_date}.xml",
                        callback=self.parse_sitemap,
                    )
            else:
                for url in (
                    Selector(response, type="xml")
                    .xpath("//sitemap:loc/text()", namespaces=self.namespace)
                    .getall()
                ):
                    yield scrapy.Request(url, callback=self.parse_sitemap)
        else:
            thumbnail_image1 = response.css("div.newsUne-media img::attr(src)").getall()
            thumbnail_image2 = response.css(
                "div.horizontalCardImg-media picture img::attr(src)"
            ).getall()
            thumbnail_image3 = response.css(
                "div.homeBlockCategory-list > a.horizontalCardTxt-item::attr(href)"
            ).getall()
            thumbnail_image = thumbnail_image1 + thumbnail_image2 + thumbnail_image3
            logo_url = response.css(
                'meta[name="twitter:image"]::attr(content)'
            ).getall()
            logo_width = response.css(
                "meta[property='twitter:image:width']::attr('content')"
            ).get()
            logo_height = response.css(
                "meta[property='twitter:image:height']::attr('content')"
            ).get()
            article_links1 = response.css("a.newsUne-item::attr(href)").getall()
            article_links2 = response.css(
                "a.horizontalCardTxt-item::attr(href)"
            ).getall()
            article_links = article_links1 + article_links2
            for index, link in enumerate(article_links):
                yield scrapy.Request(
                    link,
                    callback=self.parse_article,
                    cb_kwargs={
                        "thumbnail": thumbnail_image[index],
                        "link": article_links[index],
                        "logo_url": logo_url,
                        "logo_width": logo_width,
                        "logo_height": logo_height,
                    },
                )

    def parse_sitemap(self, response):
        """
        parse sitemap from sitemap url and callback parser to parse title and link
        """
        for article_url in (
            Selector(response, type="xml")
            .xpath("//sitemap:loc/text()", namespaces=self.namespace)
            .getall()
        ):
            yield scrapy.Request(article_url, callback=self.parse_sitemap_article)

    def parse_sitemap_article(self, response):
        """
        parse sitemap articles and  scrap title and link
        """
        title = response.css("h1.article-title::text").get()
        if title:
            article = {"link": response.url, "title": title}
            self.articles.append(article)

    def date_in_date_range(self, published_date):
        """
        return true if date is in given start date and end date range
        """
        published_date = datetime.strptime(published_date.strip(), "%d/%m/%Y %H:%M")
        if not self.date_range_lst:
            return True  # for when no start_date and end_date is given
        if published_date.date() in self.date_range_lst:
            return True
        else:
            return False

    def parse_article(
        self, response, thumbnail, link, logo_url, logo_width, logo_height
    ):
        """
        parse article and append related data to class's articles variable
        """
        published_date = response.css(
            "time.article-metas > span.article-metas__date::text"
        ).getall()
        try:
            modified_date = response.css(
                "time span.article-metas__date--update::text"
            ).getall()
        except:
            modified_date = None

        # filter by date given and breaks if date is not in date range
        if not self.date_in_date_range(
            modified_date[0] if modified_date else published_date[0]
        ):
            return

        articles_category = response.css("div.breadcrumb a::text").getall()
        content_type = response.headers.get("Content-Type").decode("utf-8")
        description = response.css(
            "header.article-header > p.article-chapo::text"
        ).getall()

        language = response.css("html::attr(lang)").getall()
        text = response.css("div.article-content p::text").getall()
        images = response.css("div.asset-image figure picture img::attr(src)").getall()
        caption = response.css("div.asset-image div.caption::text").getall()
        tags = response.css(
            "#habillagepub > div > div.website > div.container > article > div > div.pageContent-left.margin-top-xl > div.articleTags > div > a::text"
        ).getall()
        author_name = response.css(
            "div.article-sources > div.article-author::text"
        ).getall()
        publisher_name = response.xpath(
            '//*[@class="site-footer__branding__legal"]/text()'
        ).getall()
        headline = response.css("header.article-header > h1::text").getall()
        alternativeheadline = response.css(
            "header.article-header > p.article-chapo::text"
        ).getall()

        article = {
            "raw_response": {
                "content_type": content_type,
                "content": response.text,
                "language": language,
                "country": "France",
            },
            "parsed_json": {
                "main": {
                    "@type": "NewsArticle",
                    "mainEntityOfPage": {"@type": "WebPage", "@id": link},
                    "headlines": headline,
                    "alternativeheadlines": alternativeheadline,
                    "datepublished": published_date,
                    "publisher": [
                        {
                            "@id": "www.huffingtonpost.fr",
                            "@type": "NewsMediaOrganization",
                            "name": publisher_name,
                            "logo": {
                                "type": "ImageObject",
                                "url": logo_url,
                                "width": {
                                    "type": "Distance",
                                    "name": f"{logo_width} px",
                                },
                                "height": {
                                    "type": "Distance",
                                    "name": f"{logo_height} px",
                                },
                            },
                        }
                    ],
                }
            },
            "parsed_data": {
                "author": [
                    {
                        "@type": "Person",
                        "name": [author.strip() for author in author_name],
                    }
                ],
                "description": description,
                "modified_at": modified_date,
                "published_at": published_date,
                "retrieved_at": [datetime.today().strftime("%Y-%m-%d")],
                "publisher": [
                    {
                        "@id": "www.huffpost.com",
                        "@type": "NewsMediaOrganization",
                        "name": publisher_name,
                        "logo": {
                            "type": "ImageObject",
                            "url": logo_url,
                            "width": {"type": "Distance", "name": f"{logo_width} px"},
                            "height": {"type": "Distance", "name": f"{logo_height} px"},
                        },
                    }
                ],
                "text": text,
                "thumbnail_image": [thumbnail],
                "title": headline,
                "images": [
                    {"link": img, "caption": cap}
                    for img, cap in itertools.zip_longest(
                        images, caption, fillvalue=None
                    )
                ],
                "video": {"link": None, "caption": None},
                "section": articles_category,
                "tags": tags,
            },
        }
        self.articles.append(article)

    def closed(self, response):
        """
        store all scrapped data into json file with given date in filename
        """
        if self.category == "sitemap":
            filename = f'huffpost-sitemap-{self.scrape_start_date.strftime("%Y-%m-%d") if self.scrape_start_date else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}{" - "+self.scrape_end_date.strftime("%Y-%m-%d") if self.scrape_end_date else ""}.json'
        elif self.category == "articles":
            filename = f'huffpost-articles-{self.scrape_start_date.strftime("%Y-%m-%d") if self.scrape_start_date else datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}{" - "+self.scrape_end_date.strftime("%Y-%m-%d") if self.scrape_end_date else ""}.json'
        with open(f"{filename}.json", "w") as f:
            json.dump(self.articles, f, indent=4)


if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(HuffPostSpider, category="articles")
    process.start()
