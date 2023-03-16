# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class NewtonScrappingItem(scrapy.Item):
    # define the fields for your item here like:
    titles = scrapy.Field()

    content_type = scrapy.Field()
    description = scrapy.Field()
    published_date = scrapy.Field()
    language = scrapy.Field()
    text = scrapy.Field()
    images = scrapy.Field()
    caption = scrapy.Field()
    tags = scrapy.Field()
    author_name = scrapy.Field()
    publisher_name = scrapy.Field()
    headline = scrapy.Field()
    alternativeheadline = scrapy.Field()
    copyright = scrapy.Field()
    images_data = scrapy.Field()
    social_site = scrapy.Field()
    social_url = scrapy.Field()
