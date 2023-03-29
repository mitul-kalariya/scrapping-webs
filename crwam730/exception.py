# Exception
# exceptions.py
class InvalidDateException(Exception):
    """Raise when invalid date is passed"""
    pass


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

    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from sitemap"""

    pass


class ExportOutputFileException(Exception):
    """Raise when exception arise while exporting output file"""

    pass


class ServiceUnavailableException(Exception):
    """Rise when getting 403, 406, 429 or >500 status code"""

    pass


class URLNotFoundException(Exception):
    """Rise when getting 404 status code"""

    pass