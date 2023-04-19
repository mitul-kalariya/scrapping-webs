# Exception
# exceptions.py


class InvalidArgumentException(Exception):
    """Raise when invalid date is passed"""

    pass


class InputMissingException(Exception):
    """Raise when any of the required input is missing"""

    pass


class SitemapScrappingException(Exception):
    """Raise when exception arise while fetching sitemap"""

    pass


class SitemapArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use SitemapArticleScrappingException(f"Error occurred while fetching article details from sitemap:- {str(e)}")
    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    # Use ArticleScrappingException(f"Error occurred while fetching article details:- {str(e)}")
    pass


class ProxyConnectionException(Exception):
    """Rise when getting 403 or 407 status code"""
    pass
