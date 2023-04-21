"""Exceptions"""


class InvalidDateException(Exception):
    """Raise when invalid date is passed"""
    pass


class InvalidInputException(Exception):
    """Raise when invalid input is given"""
    pass


class CategoryScrappingException(Exception):
    """Raise when exception arise while fetching category links"""
    pass


class ArticleScrappingException(Exception):
    """Raise when exception arise while fetching article details from category"""
    pass


class ExportOutputFileException(Exception):
    """Raise when exception arise while exporting output file"""
    pass


class URLNotFoundException(Exception):
    """Rise when getting 404 status code"""
    pass


class ParseFunctionFailedException(Exception):
    """An exception raised when parse function fails."""
    pass


class ProxyConnectionException(Exception):
    """Rise when getting 403 or 407 status code"""
    pass
