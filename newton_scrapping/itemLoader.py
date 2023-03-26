from itemloaders.processors import (
    TakeFirst,
    MapCompose,
    Identity
)
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from newton_scrapping.constant import (
    TYPE,
    LIST_OF_PARSED_JSON_OBJECT,
    NEWS_ARTICLE,
    IMAGE_GALLERY,
    VIDEO_OBJECT
)


def other_filter(values):
    lst_other = []
    for v in values:
        if v.get(TYPE) not in LIST_OF_PARSED_JSON_OBJECT:
            lst_other.append(v)
    return lst_other


def main_filter(values):
    for v in values:
        if v.get(TYPE) == NEWS_ARTICLE:
            return v


def image_gallery_filter(values):
    for v in values:
        if v.get(TYPE) == IMAGE_GALLERY:
            return v


def video_object_filter(values):
    for v in values:
        if v.get(TYPE) == VIDEO_OBJECT:
            return v


class ArticleDataLoader(ItemLoader):
    default_output_processor = TakeFirst()


class ArticleRawResponseLoader(ItemLoader):
    default_output_processor = TakeFirst()
    content_type_in = MapCompose(remove_tags)


class ArticleRawParsedJsonLoader(ItemLoader):
    default_output_processor = TakeFirst()
    main_in = MapCompose(main_filter)
    ImageGallery_in = MapCompose(image_gallery_filter)
    VideoObject_in = MapCompose(video_object_filter)
    other_in = MapCompose(other_filter)
    other_out = Identity()
