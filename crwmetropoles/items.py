# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy import Item, Field
from itemloaders.processors import TakeFirst, MapCompose
from w3lib.html import remove_tags



class NewtonScrappingItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class ArticleData(Item):
    raw_response = Field(output_processor=TakeFirst())
    parsed_json = Field(output_processor=TakeFirst())
    parsed_data = Field(output_processor=TakeFirst())


class ArticleRawResponse(Item):
    content_type = Field(
        input_processor=MapCompose(remove_tags), output_processor=TakeFirst()
    )
    content = Field(output_processor=TakeFirst())


class ArticleRawParsedJson(Item):
    main = Field()
    misc = Field()