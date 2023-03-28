"""constants"""

# Initial url for sitemap
SITEMAP_URL = "https://www.leparisien.fr/arc/outboundfeeds/news-sitemap-index/?from=0&outputType=xml&_website" \
              "=leparisien"

DATE_FORMAT = '%Y-%m-%d'
TYPE = "@type"

# Used in itemLoader.py for main field's output processor
NEWS_ARTICLE = "NewsArticle"

# Used in itemLoader.py for ImageGallery field's output processor
IMAGE_GALLERY = "ImageGallery"

# Used in itemLoader.py for VideoObject field's output processor
VIDEO_OBJECT = "VideoObject"


# Used in itemLoader.py for other field's output processor
LIST_OF_PARSED_JSON_OBJECT = [NEWS_ARTICLE, IMAGE_GALLERY, VIDEO_OBJECT]

# Used in utils.py for providing parsed data keys of base dictionary
PARSED_DATA_KEYS_LIST = [
    "source_country",
    "source_language",
    "author",
    "description",
    "modified_at",
    "published_at",
    "publisher",
    "text",
    "thumbnail_image",
    "title",
    "images",
    "section",
    "tags",
    "embed_video_link",
]
