# Exception
# exceptions.py
class InvalidDateException(Exception):
    """Raise when invalid date is passed"""

    # Use InvalidDateException("Please enter valid date")
    pass


class InvalidInputException(Exception):
    """Raise when invalid input is given"""

    pass


class SitemapScrappingException(Exception):
    """Raise when exception arise while fetching sitemap"""

    # Use SitemapScrappingException(f"Error occurred while fetching sitemap:- {str(e)}")
    pass


class SitemapArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use SitemapArticleScrappingException(f"Error occurred while fetching article details from sitemap:- {str(e)}")
    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use ArticleScrappingException(f"Error occurred while fetching article details:- {str(e)}")
    pass


class ExportOutputFileException(Exception):
    """Raise when exception arise while exporting output file"""

    # Use ExportOutputFileException(f"Error occurred while exporting file:- {str(e)}")
    pass


class ParseFunctionFailedException(Exception):
    """An exception raised when parse function fails."""

    # use ParseFunctionFailedException(f"Error occured in parse function: {e}")
    pass


class ProxyConnectionException(Exception):
    """Rise when getting 403 or 407 status code"""
    pass
