import logging
import unittest

from crwhk01 import Crawler
from crwhk01.spiders.hk01 import HK01Spider
from crwhk01.test.helpers.constant import SITEMAP_URL, TEST_ARTICLES
from crwhk01.test.helpers.utils import get_article_content, online_response_from_url

# Creating an object
logger = logging.getLogger()


class TestArticle(unittest.TestCase):
    def _test_article_results(self, articles, test_data_path):
        article = [article for article in articles]
        test_article_data = get_article_content(test_data_path)
        self._test_raw_response(article, test_article_data)
        self._test_parse_json(article, test_article_data)
        self._test_parse_json_with_test_data(article, test_article_data)
        self._test_parse_json_data_format(article, test_article_data)

    # This is first function called by crawler so testing the main function will cover all scenarios
    def test_parse(self):
        for article in TEST_ARTICLES:
            logger.info(f"Testing article with URL:- {article['url']}")
            spider = HK01Spider(type="article", url=article["url"])
            articles = spider.parse(online_response_from_url(spider.article_url))
            self._test_article_results(articles, article["test_data_path"])
            logger.info(f"Testing completed article with URL:- {article['url']}")

    def _test_raw_response(self, article, test_article_data):
        # Testing raw_response object
        with self.subTest():
            self.assertEqual(
                article[0].get("raw_response").get("content_type"),
                test_article_data[0].get("raw_response").get("content_type"),
            )
        with self.subTest():
            self.assertIsInstance(article[0].get("raw_response").get("content")[0], str)

    def _test_parse_json(self, article, test_article_data):
        # Testing parsed_json object
        # it may be possible that we don't get either misc or main for some websites.
        # In that case we will exclude the parsed_json object
        if test_article_data[0].get("parsed_json"):
            with self.subTest():
                if test_article_data[0].get("parsed_json").get("main"):
                    self.assertIsInstance(
                        article[0].get("parsed_json").get("main"), dict
                    )
            with self.subTest():
                if test_article_data[0].get("parsed_json").get("misc"):
                    self.assertIsInstance(
                        article[0].get("parsed_json").get("misc"), list
                    )
            with self.subTest():
                if test_article_data[0].get("parsed_json").get("imageObjects"):
                    self.assertIsInstance(article[0].get("parsed_json").get("imageObjects"), list,
                                          "parsed_json --> imageObjects must be list")
            with self.subTest():
                if test_article_data[0].get("parsed_json").get("videoObjects"):
                    self.assertIsInstance(article[0].get("parsed_json").get("videoObjects"), list,
                                          "parsed_json --> videoObjects must be list")
            with self.subTest():
                if test_article_data[0].get("parsed_json").get("other"):
                    self.assertIsInstance(article[0].get("parsed_json").get("other"), list,
                                          "parsed_json --> other must be list")
                if test_article_data[0].get("parsed_json").get("Other"):
                    self.assertIsInstance(article[0].get("parsed_json").get("other"), list,
                                          "parsed_json --> other must be list")

    def _test_parse_json_with_test_data(self, article, test_article_data):
        # Testing parsed_data object

        with self.subTest():
            self.assertDictEqual(
                article[0].get("parsed_data").get("author")[0],
                test_article_data[0].get("parsed_data").get("author")[0],
                "author mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("published_at"),
                test_article_data[0].get("parsed_data").get("published_at"),
                "published_at mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("publisher"),
                test_article_data[0].get("parsed_data").get("publisher"),
                "publisher mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("section"),
                test_article_data[0].get("parsed_data").get("section"),
                "section mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("tags"),
                test_article_data[0].get("parsed_data").get("tags"),
                "tags mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("source_country"),
                test_article_data[0].get("parsed_data").get("source_country"),
                "source_country mismatch in parsed_data",
            )
        with self.subTest():
            self.assertEqual(
                article[0].get("parsed_data").get("source_language"),
                test_article_data[0].get("parsed_data").get("source_language"),
                "source_language mismatch in parsed_data",
            )

    def _test_image_format(self, article):
        # Testing the image object inside parsed_data
        article_images = article[0].get("parsed_data").get("images")
        if article_images:
            for image in article_images:
                with self.subTest():
                    self.assertIsNotNone(
                        image.get("link"),
                        "missing object:- parsed_data--> images --> link",
                    )

    def _test_author_format(self, article):
        # Testing the author object inside parsed_data
        article_authors = article[0].get("parsed_data").get("authors")
        if article_authors:
            for author in article_authors:
                with self.subTest():
                    self.assertIsNotNone(
                        author.get("@type"),
                        "missing object:- parsed_data--> author --> @type",
                    )
                with self.subTest():
                    self.assertIsNotNone(
                        author.get("name"),
                        "missing object:- parsed_data--> author --> name",
                    )
                with self.subTest():
                    self.assertIsNotNone(
                        author.get("url"),
                        "missing object:- parsed_data--> author --> url",
                    )

    def _test_parse_json_data_format(self, article, test_article_data):  # noqa: C901
        # Since the content of article can be modified at anytime so not checkering exact text
        # but testing the object format so that we can verify that crawler is working well.
        if article[0].get("parsed_data").get("text"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("text")[0],
                    str,
                    "format mismatch for parsed_data--> text",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("text"),
                    list,
                    "format mismatch for parsed_data--> text",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> text")

        if article[0].get("parsed_data").get("title"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("title")[0],
                    str,
                    "format mismatch for parsed_data--> title",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("title"),
                    list,
                    "format mismatch for parsed_data--> title",
                )
        else:
            raise AssertionError("missing object:- parsed_data--> title")

        if article[0].get("parsed_data").get("description"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("description")[0],
                    str,
                    "format mismatch for parsed_data--> description",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("description"),
                    list,
                    "format mismatch for parsed_data--> description",
                )
        else:
            raise AssertionError("missing object:- parsed_data--> description")

        if article[0].get("parsed_data").get("source_country"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("source_country")[0],
                    str,
                    "format mismatch for parsed_data--> source_country",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("source_country"),
                    list,
                    "format mismatch for parsed_data--> source_country",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> source_country")

        if article[0].get("parsed_data").get("source_language"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("source_language")[0],
                    str,
                    "format mismatch for parsed_data--> source_language",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("source_language"),
                    list,
                    "format mismatch for parsed_data--> source_language",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> source_language")

        if article[0].get("parsed_data").get("author"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("author")[0],
                    dict,
                    "format mismatch for parsed_data--> author",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("author"),
                    list,
                    "format mismatch for parsed_data--> author",
                )
            self._test_author_format(article)
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> author")

        if article[0].get("parsed_data").get("modified_at"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("modified_at")[0],
                    str,
                    "format mismatch for parsed_data--> modified_at",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("modified_at"),
                    list,
                    "format mismatch for parsed_data--> modified_at",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> modified_at")

        if article[0].get("parsed_data").get("published_at"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("published_at")[0],
                    str,
                    "format mismatch for parsed_data--> published_at",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("published_at"),
                    list,
                    "format mismatch for parsed_data--> published_at",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> published_at")

        if article[0].get("parsed_data").get("publisher"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("publisher")[0],
                    dict,
                    "format mismatch for parsed_data--> publisher",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("publisher"),
                    list,
                    "format mismatch for parsed_data--> publisher",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> publisher")

        if article[0].get("parsed_data").get("images"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("images")[0],
                    dict,
                    "format mismatch for parsed_data--> images",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("images"),
                    list,
                    "format mismatch for parsed_data--> images",
                )
            self._test_image_format(article)
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> images")

        if article[0].get("parsed_data").get("section"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("section")[0],
                    str,
                    "format mismatch for parsed_data--> section",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("section"),
                    list,
                    "format mismatch for parsed_data--> section",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> section")

        if article[0].get("parsed_data").get("tags"):
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("tags")[0],
                    str,
                    "format mismatch for parsed_data--> tags",
                )
            with self.subTest():
                self.assertIsInstance(
                    article[0].get("parsed_data").get("tags"),
                    list,
                    "format mismatch for parsed_data--> tags",
                )
        else:
            with self.subTest():
                raise AssertionError("missing object:- parsed_data--> tags")


class TestSitemap(unittest.TestCase):
    def setUp(self):
        self.type = "sitemap"
        self.crawler = Crawler(query={"type": "link_feed", "domain": SITEMAP_URL})

    def _test_sitemap_article_format(self):
        # Testing the sitemap article object
        for article in self.article_urls:
            with self.subTest():
                self.assertIsNotNone(
                    article.get("link"), "missing object:- sitemap articles --> link"
                )
            with self.subTest():
                self.assertIsNotNone(
                    article.get("title"), "missing object:- sitemap articles --> title"
                )

    def _test_sitemap_results(self):
        with self.subTest():
            self.assertGreater(
                len(self.article_urls),
                0,
                "Crawler did not fetched single article form sitemap",
            )
        with self.subTest():
            self.assertIsInstance(
                self.article_urls, list, "Sitemap Article format mismatch"
            )
        with self.subTest():
            self.assertIsInstance(
                self.article_urls[0], dict, "Sitemap Article format mismatch"
            )
        self._test_sitemap_article_format()

    def test_parse(self):
        self.article_urls = self.crawler.crawl()
        self._test_sitemap_results()


if __name__ == "__main__":
    unittest.main()
