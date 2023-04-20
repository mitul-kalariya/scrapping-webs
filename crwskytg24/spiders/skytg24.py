import logging
from datetime import datetime, date
from abc import ABC, abstractmethod
import scrapy

from scrapy.loader import ItemLoader

from crwskytg24 import exceptions
from crwskytg24.constant import SITEMAP_URL, LOGGER, TODAYS_DATE, BASE_URL
from crwskytg24.items import ArticleData
from crwskytg24.utils import (
    validate_sitemap_date_range,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    export_data_to_json_file,
    date_range,
)
header = {
"cookie": "G_ENABLED_IDPS=google; _gid=GA1.2.502370223.1681793505; __lxG__consent__v2=1%7C1%7C1681793505584%7C192%7C1683521507150%7C2%7C1%7C1%7C1681793507091%7C1%7C16817935048459150; __lxG__consent__v2_daisybit=CPqbVLQPqbVLfA_ADAITDACsAP_AAAAAAAAAJXNd_H__bX9r-f5_6ft0eY1f9_r77uQzDhfNk-4F3L_W_LwX_2E7NF36tq4KmR4ku3LBIUNlHNHUDVmwaokVrzHsak2cpTNKJ6BEkHMZe2dYGF5vmxtj-QKY5_5_d3b52T-9_dv-39z3391Xv3d5_-_12PDdU5_9Dfn9fR_b-9KP9_78v8v8_9_rk2_e3_3____7_H_-f_BK6AAASEgAwABBK4NABgACCVwiADAAEErhUAGAAIJXDIAMAAQSuHQAYAAglcQgAwABBK4lABgACCVxSADAAEErgAAA.YAAAAAAAAAAA; __lxG__consent__v2_gdaisybit=~1~39.43969.13.64.15.952.11.17132.10.354.21.4697.12.92.18.7.20.5.20.6514.11..29.4.14.453.10.62966944.29.453162.19.1.17..10.91862834.146..50..15.1.17.1.18..25..10..25.5.18.97.41.24.18..24.427652.14..18.73228.28.863.10.4.20.2.13.464.11.13.22..16.26824.11.65.33..11.81.10..28..12.1.24.27619.30..17.49.15.873.12.72417.12..13..22..13.2.12.2.10.14.15.2494547.13.5.15.4.13.4.14..10..15.2562212.14.74829.10..18..12..13.2.18.113119.25.41.19.84535484222.14.2.13.4269632235236.10..11.63.19..11.31239.19..11..15.3.10..13.434633331116.11.311.11.61.10.52632243227.15.7.14.1334543225411291691537.10..11.1311213261.12.813112277141261211311411218174321353961.15..10..28.122.12.34163471311315313411421212224212224111221111211122112121712212111121132118116216232111223114112211431412123112411151363152341231421222111111.11.131122523351116112519513171451721112111421.12.113122312111213111124151243822972212146171126312.201..300.; _pbjs_userid_consent_data=6487473709414028; __gads=ID=e9a501b6610442fd:T=1681793507:S=ALNI_MZWi-5QJ8AhLZbPkDD709QxJIIXdg; _fbp=fb.1.1681892282129.2143436062; _pubcid=17306ca2-f872-4427-b938-68c8d6832706; _lr_env_src_ats=false; panoramaId_expiry=1681982901919; _cc_id=11a8c928cb6ee7d44f767f80ae273711; panoramaId=02086879874864c883018d2a271da9fb927a63a50d8df45c5efe420247c6d16a; pbjs-unifiedid=%7B%22TDID%22%3A%227c0fffda-809a-463d-a629-f44f2af75fda%22%2C%22TDID_LOOKUP%22%3A%22TRUE%22%2C%22TDID_CREATED_AT%22%3A%222023-03-19T09%3A28%3A21%22%7D; _ga_NFF0RV6Y1Z=GS1.1.1681960369.8.0.1681960369.0.0.0; _ga=GA1.2.2093465452.1681793505; __gpi=UID=00000bf79c656247:T=1681793507:RT=1681960372:S=ALNI_MZFcXmzrlvc_rjB3Pj0JhCv5cNTXQ; cto_bundle=WIqir19OckpIUU5kb0k4bjVTN2dET2ZlUU1BQmVBZ0FrTmU5ZSUyRnZPRE1IQkwlMkJHS0Zvb1pRRk1sWVpuTGhaOFNlS0hrYW5KbkxLM0tCTUFsMmpySEhRS0EzSnNPb0JpJTJGQWFOYm9sJTJGTVVOaUo0TGRaeVFJQmhpdndLZ2tlcDY3YmFuUDhLcHR4azVZdUpiZld2anhaV09LQ3BXdDkxVXRCWldITnNBTk8wV3lCJTJCZTVNJTNE; cto_bidid=WIqir19OckpIUU5kb0k4bjVTN2dET2ZlUU1BQmVBZ0FrTmU5ZSUyRnZPRE1IQkwlMkJHS0Zvb1pRRk1sWVpuTGhaOFNlS0hrYW5KbkxLM0tCTUFsMmpySEhRS0EzSnNPb0JpJTJGQWFOYm9sJTJGTVVOaUo0TGRaeVFJQmhpdndLZ2tlcDY3YmFuUDhLcHR4azVZdUpiZld2anhaV09LQ3BXdDkxVXRCWldITnNBTk8wV3lCJTJCZTVNJTNE; wt_rla=458677892662477%2C2%2C1681960373547; cf_clearance=nNepvL5zjrTicPW.q4XrhvIIKaABO9.XYBwl78k8tBE-1681969611-0-160",
"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
}
cookie = {'cookie': "G_ENABLED_IDPS=google; _gid=GA1.2.502370223.1681793505; __lxG__consent__v2=1%7C1%7C1681793505584%7C192%7C1683521507150%7C2%7C1%7C1%7C1681793507091%7C1%7C16817935048459150; __lxG__consent__v2_daisybit=CPqbVLQPqbVLfA_ADAITDACsAP_AAAAAAAAAJXNd_H__bX9r-f5_6ft0eY1f9_r77uQzDhfNk-4F3L_W_LwX_2E7NF36tq4KmR4ku3LBIUNlHNHUDVmwaokVrzHsak2cpTNKJ6BEkHMZe2dYGF5vmxtj-QKY5_5_d3b52T-9_dv-39z3391Xv3d5_-_12PDdU5_9Dfn9fR_b-9KP9_78v8v8_9_rk2_e3_3____7_H_-f_BK6AAASEgAwABBK4NABgACCVwiADAAEErhUAGAAIJXDIAMAAQSuHQAYAAglcQgAwABBK4lABgACCVxSADAAEErgAAA.YAAAAAAAAAAA; __lxG__consent__v2_gdaisybit=~1~39.43969.13.64.15.952.11.17132.10.354.21.4697.12.92.18.7.20.5.20.6514.11..29.4.14.453.10.62966944.29.453162.19.1.17..10.91862834.146..50..15.1.17.1.18..25..10..25.5.18.97.41.24.18..24.427652.14..18.73228.28.863.10.4.20.2.13.464.11.13.22..16.26824.11.65.33..11.81.10..28..12.1.24.27619.30..17.49.15.873.12.72417.12..13..22..13.2.12.2.10.14.15.2494547.13.5.15.4.13.4.14..10..15.2562212.14.74829.10..18..12..13.2.18.113119.25.41.19.84535484222.14.2.13.4269632235236.10..11.63.19..11.31239.19..11..15.3.10..13.434633331116.11.311.11.61.10.52632243227.15.7.14.1334543225411291691537.10..11.1311213261.12.813112277141261211311411218174321353961.15..10..28.122.12.34163471311315313411421212224212224111221111211122112121712212111121132118116216232111223114112211431412123112411151363152341231421222111111.11.131122523351116112519513171451721112111421.12.113122312111213111124151243822972212146171126312.201..300.; _pbjs_userid_consent_data=6487473709414028; __gads=ID=e9a501b6610442fd:T=1681793507:S=ALNI_MZWi-5QJ8AhLZbPkDD709QxJIIXdg; _fbp=fb.1.1681892282129.2143436062; _pubcid=17306ca2-f872-4427-b938-68c8d6832706; _lr_env_src_ats=false; panoramaId_expiry=1681982901919; _cc_id=11a8c928cb6ee7d44f767f80ae273711; panoramaId=02086879874864c883018d2a271da9fb927a63a50d8df45c5efe420247c6d16a; pbjs-unifiedid=%7B%22TDID%22%3A%227c0fffda-809a-463d-a629-f44f2af75fda%22%2C%22TDID_LOOKUP%22%3A%22TRUE%22%2C%22TDID_CREATED_AT%22%3A%222023-03-19T09%3A28%3A21%22%7D; _ga_NFF0RV6Y1Z=GS1.1.1681960369.8.0.1681960369.0.0.0; _ga=GA1.2.2093465452.1681793505; __gpi=UID=00000bf79c656247:T=1681793507:RT=1681960372:S=ALNI_MZFcXmzrlvc_rjB3Pj0JhCv5cNTXQ; cto_bundle=WIqir19OckpIUU5kb0k4bjVTN2dET2ZlUU1BQmVBZ0FrTmU5ZSUyRnZPRE1IQkwlMkJHS0Zvb1pRRk1sWVpuTGhaOFNlS0hrYW5KbkxLM0tCTUFsMmpySEhRS0EzSnNPb0JpJTJGQWFOYm9sJTJGTVVOaUo0TGRaeVFJQmhpdndLZ2tlcDY3YmFuUDhLcHR4azVZdUpiZld2anhaV09LQ3BXdDkxVXRCWldITnNBTk8wV3lCJTJCZTVNJTNE; cto_bidid=WIqir19OckpIUU5kb0k4bjVTN2dET2ZlUU1BQmVBZ0FrTmU5ZSUyRnZPRE1IQkwlMkJHS0Zvb1pRRk1sWVpuTGhaOFNlS0hrYW5KbkxLM0tCTUFsMmpySEhRS0EzSnNPb0JpJTJGQWFOYm9sJTJGTVVOaUo0TGRaeVFJQmhpdndLZ2tlcDY3YmFuUDhLcHR4azVZdUpiZld2anhaV09LQ3BXdDkxVXRCWldITnNBTk8wV3lCJTJCZTVNJTNE; wt_rla=458677892662477%2C2%2C1681960373547; cf_clearance=nNepvL5zjrTicPW.q4XrhvIIKaABO9.XYBwl78k8tBE-1681969611-0-160"}

class BaseSpider(ABC):
    """
    Base class for making abstract methods
    """
    # pylint: disable=unnecessary-pass

    @abstractmethod
    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        pass


    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error
            while parsing the sitemap page.
        """
        pass

    def parse_sitemap_article(self, response: str) -> None:
        """Extracts article titles and links from the response object
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.
        Args:
            response (scrapy.http.Response): The response object containing the article data.
        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        pass


class SkyTg24Spider(scrapy.Spider, BaseSpider):
    """Spider"""

    name = "skytg24"
    def __init__(self, *args, type=None, url=None, since=None, until=None, **kwargs):
        """
        Initializes a web scraper object to scrape data from a website or sitemap.
        Args:
            type (str): A string indicating the type of data to scrape. Must be either
            "sitemap" or "article".
            since (str): A string representing the start date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            url (str): A string representing the URL of the webpage to be scraped.
            until (str): A string representing the end date of the sitemap to be scraped.
            Must be in the format "YYYY-MM-DD".
            **kwargs: Additional keyword arguments that can be used to pass
            information to the web scraper.
        Raises:
            InvalidInputException: If a URL is not provided for an "article" type scraper.
        Notes:
            This function initializes a web scraper object and sets various
            properties based on the arguments passed.
            If the type argument is "sitemap", the start and end dates of
            the sitemap are validated and set.
            If the type argument is "article",
            the URL to be scraped is validated and set. A log file is created for the web scraper.
        """
        try:
            super(SkyTg24Spider, self).__init__(*args, **kwargs)
            self.output_callback = kwargs.get("args", {}).get("callback", None)
            self.start_urls = []
            self.date_range_lst = []
            self.articles = []
            self.article_url = url
            self.type = type.lower()
            self.today = date.today().strftime("%Y-%m-%d")
            self.proxies = kwargs.get('args', {}).get('proxies', None)

            if self.type == "sitemap":
                self.start_urls.append(SITEMAP_URL)

                self.since = (
                    datetime.strptime(since, "%Y-%m-%d").date() if since else None
                )
                self.until = (
                    datetime.strptime(until, "%Y-%m-%d").date() if until else None
                )
                validate_sitemap_date_range(since, until)

            if self.type == "article":
                if url:
                    self.start_urls.append(url)
                else:
                    LOGGER.info("Must have a URL to scrap")
                    raise exceptions.InvalidInputException("Must have a URL to scrap")

        except Exception as exception:
            LOGGER.info(
                "Error occured in init function in %s :-- %s", self.name, exception
            )
            raise exceptions.InvalidInputException(
                f"Error occured in init function in {self.name}:-- {exception}"
            )

    def parse(self, response):
        """
        Parses the given Scrapy response based on the specified type of parsing.
        Returns:
            A generator that yields a scrapy.Request object to parse a sitemap or an article.
        Example Usage:
            parse(scrapy.http.Response(url="https://example.com", body="..."))
        """
        try:
            if self.type == "sitemap":
                yield scrapy.Request(
                    response.url, callback=self.parse_sitemap,headers=header
                )

            elif self.type == "article":
                article_data = self.parse_article(response)
                yield article_data

        except BaseException as exception:
            LOGGER.info("Error occured in parse function: %s", exception)
            raise exceptions.ParseFunctionFailedException(
                f"Error occured in parse function: {exception}"
            )

    def parse_sitemap(self, response):
        """Parses a sitemap page and extracts links and titles for further processing.
        Args:
            response (scrapy.http.Response): The HTTP response object
            containing the sitemap page.
        Yields:
            scrapy.http.Request: A request object for each link on the sitemap page.
        Raises:
            exceptions.SitemapScrappingException: If there is an error
            while parsing the sitemap page.
        """

        try:
            if "sitemap.xml" in response.url:
                if self.since and self.until:
                    since = str(self.since.month) + str(self.since.year)
                    until = str(self.until.month) + str(self.until.year)
                    if since == until:
                        date = self.since.strftime("%Y-%m-%d").split("-")
                        link = f"https://www.ilfattoquotidiano.it/sitemap-pt-post-{date[0]}-{date[1]}.xml"

                        abc = scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            headers=header,
                            cookies=cookie
                        )
                        breakpoint()
                        print(abc)
                        yield scrapy.Request(
                            link,
                            callback=self.parse_sitemap_article,
                            headers=header,
                            cookies=cookie
                        )


                    else:
                        since_date = self.since.strftime("%Y-%m-%d").split("-")
                        until_date = self.until.strftime("%Y-%m-%d").split("-")
                        links = [
                            f"https://www.ilfattoquotidiano.it/sitemap-pt-post-{since_date[0]}-{since_date[1]}.xml",
                            f"https://www.ilfattoquotidiano.it/sitemap-pt-post-{until_date[0]}-{until_date[1]}.xml",
                        ]
                        for link in links:
                            yield scrapy.Request(
                                link,
                                dont_filter=True,
                                callback=self.parse_sitemap_article,
                            )
                else:
                    current_date = TODAYS_DATE.strftime("%Y-%m-%d").split("-")
                    link = (
                            f"https://www.ilfattoquotidiano.it/sitemap-pt-post-{current_date[0]}-{current_date[1]}.xml"
                    )
                    yield scrapy.Request(
                        link, dont_filter=True, callback=self.parse_sitemap_article
                    )

        except BaseException as exception:
            LOGGER.info("Error while parsing sitemap: %s", exception)
            raise exceptions.SitemapScrappingException(
                f"Error while parsing sitemap: {str(exception)}"
            )

    def parse_sitemap_article(self, response):
        """Extracts article titles and links from the response object
        and yields a Scrapy request for each article.
        Args:
            self: The Scrapy spider instance calling this method.
            response: The response object obtained after making a request to a sitemap URL.
        Yields:
            A Scrapy request for each article URL in the sitemap, with the `parse_sitemap_datewise`
            method as the callback and the article link and title as metadata.
        Raises:
            SitemapArticleScrappingException: If an error occurs while filtering articles by date.
        """
        try:
            namespaces = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            links = response.xpath("//sitemap:loc/text()", namespaces=namespaces).getall()
            published_date = response.xpath('//sitemap:lastmod/text()', namespaces=namespaces).getall()

            for link, pub_date in zip(links, published_date):
                publish_date = pub_date.split("T")
                published_at = datetime.strptime(publish_date[0], "%Y-%m-%d").date()
                today_date = datetime.today().date()

                if self.since and published_at < self.since:
                    return
                if self.since and published_at > self.until:
                    return

                if self.since and self.until:
                    data = {"link": link}
                    self.articles.append(data)
                elif today_date == published_at:
                    data = {"link": link}
                    self.articles.append(data)
                else:
                    continue

        except Exception as exception:
            LOGGER.info("Error while parsing sitemap article: %s", str(exception))
            raise exceptions.SitemapArticleScrappingException(
                "Error while parsing sitemap article::%s-", str(exception)
            )

    def parse_article(self, response) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.
        Args:
            response (scrapy.http.Response): The response object containing the article data.
        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        try:
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            raw_response = get_raw_response(response)
            response_json = get_parsed_json(response)
            response_data = get_parsed_data(response)
            response_data["source_country"] = ["Italy"]
            response_data["time_scraped"] = [str(datetime.now())]

            articledata_loader.add_value("raw_response", raw_response)
            articledata_loader.add_value("parsed_json", response_json)
            articledata_loader.add_value("parsed_data", response_data)

            self.articles.append(dict(articledata_loader.load_item()))

            return articledata_loader.item

        except Exception as exception:
            LOGGER.info(
                "Error occurred while scrapping an article for this link %s.",
                response.url + str(exception),
            )
            raise exceptions.ArticleScrappingException(
                f"Error occurred while fetching article details:-  {str(exception)}"
            )

    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """
        try:
            stats = self.crawler.stats.get_stats()
            if (
                    stats.get(
                        "downloader/exception_type_count/scrapy.core.downloader.handlers.http11.TunnelError",
                        0,
                    )
                    > 0
            ) or (
                    stats.get(
                        "downloader/request_count",
                        0,
                    )
                    == stats.get(
                "downloader/exception_type_count/twisted.internet.error.TimeoutError",
                0,
            )
            ):
                self.output_callback("Error in Proxy Configuration")
            if self.output_callback is not None:
                self.output_callback(self.articles)
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)

        except BaseException as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while closing crawler{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while closing crawler{str(exception)} - {reason}",
                level=logging.ERROR,
            )