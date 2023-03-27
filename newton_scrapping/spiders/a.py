import scrapy
from datetime import datetime


class MySpider(scrapy.Spider):
    name = 'aaa'
    start_urls = ['https://www.tagesschau.de/archiv/']

    def parse(self, response):
        for link in response.css('.articlePageList a'):
            url = link.attrib['href']
            if not url.startswith('https://www.tagesschau.de/'):
                url = 'https://www.tagesschau.de/' + url.lstrip('/')
            self.category_wise.append(url)

        for link in self.category_wise:
            yield scrapy.Request(link, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        for link in response.css("a"):
            url = link.css("::attr(href)").get()

            if url:
                if url.startswith(("#", "//")) or url in [
                    "https://www.ard.de",
                    "https://wetter.tagesschau.de/",
                    "https://www.tagesschau.de/",
                    "https://www.tiktok.com/legal/privacy-policy?lang=de",
                    "https://www.tiktok.com/robots.txt"
                ] or 'shtml' in url or 'mp3' in url:
                    continue
                if url.startswith("/"):
                    url = "https://www.tagesschau.de" + url

                yield scrapy.Request(url, callback=self.parse_article)

    def parse_article(self, response):
        url = response.url
        title = response.css(".seitenkopf__headline--text::text").get()

        if 'archiv' in url:
            yield scrapy.Request(url, callback=self.archiv_data)
        else:
            if url:
                yield {
                    'link': url,
                    'title': title,
                }


    def archiv_data(self, response):
        for link in response.css("a"):
            url = link.css("::attr(href)").get()
            title = link.css('.teaser-xs__headline').get()
            yield {
                "link": url,
                "title" : title,
            }


    def multimedia_data(self, response):
        url = response.url
        title = response.css('.multimediahead__headline').get()
        published_at = response.css('.multimediahead__date').get()
        date_string = published_at.split(": ")[1].split(" ")[0]  # extract date from string
        date = datetime.strptime(date_string, "%d.%m.%Y").date()  # convert date to datetime object

        if url and title and date:
            yield {
                "link" : url,
                'title': title,
                'date' : date
            }



    # def parse_article_date_wise(self, response):
    #     url = response.meta['url']
    #     title = response.meta['title']
    #     publicated_at = pass