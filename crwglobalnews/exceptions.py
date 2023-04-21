# Exception
# exceptions.py


class InvalidInputException(Exception):
    """Raise when invalid input is given"""

    pass


class SitemapScrappingException(Exception):
    """Raise when exception arise while fetching sitemap"""

    # Use SitemapScrappingException(f"Error occurred while fetching sitemap:- {str(e)}")
    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use ArticleScrappingException(f"Error occurred while fetching article details:- {str(e)}")
    pass


class ParseFunctionFailedException(Exception):
    """An exception raised when parse function fails."""

    # use ParseFunctionFailedException(f"Error occured in parse function: {e}")
    pass


class ProxyConnectionException(Exception):
    """Rise when getting 403 or 407 status code"""

    pass


class CrawlerClosingException(Exception):
    """Rise when getting error while closing crawler status code"""

    pass
