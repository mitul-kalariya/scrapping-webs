import scrapy
import json
from datetime import datetime
from scrapy.selector import Selector
from scrapy.utils.project import get_project_settings

class LeParisien(scrapy.Spider):
    name = "le_parisien"

    namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9', 'news':'http://www.google.com/schemas/sitemap-news/0.9'}

    def __init__(self, type=None, start_date=None, end_date=None,url=None, *args, **kwargs):
        super(LeParisien, self).__init__(*args, **kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type
        self.start_date = start_date
        self.end_date = end_date
        self.url = url

        if self.type == "sitemap":
            self.start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
            self.end_date = datetime.strptime(end_date, '%Y-%m-%d') if start_date else None

            if (self.end_date - self.start_date).days > 30:
                raise ValueError("Enter start_date and end_date for maximum 30 days.")
            else:
                self.start_urls.append("https://www.leparisien.fr/arc/outboundfeeds/news-sitemap-index/?from=0&outputType=xml&_website=leparisien")
        elif self.type == "article":
            if url:
                self.start_urls.append(self.url) 
            else:
                raise ValueError("For article data url is required")       
        else:
            raise ValueError("Invalid category argument. Must be 'sitemap' or 'article'.")


    def parse(self, response):
        if self.type=="sitemap":   
            for site_map_url in Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall():
                yield scrapy.Request(site_map_url, callback=self.parse_sitemap)

        elif self.type=="article":
                yield scrapy.Request(self.url, callback=self.parse_article)    
                    
    def parse_sitemap(self, response):

        article_urls = Selector(response, type='xml').xpath('//sitemap:loc/text()', namespaces=self.namespace).getall()
        published_date = Selector(response, type='xml').xpath('//news:publication_date/text()', namespaces=self.namespace).getall()
        title = Selector(response, type='xml').xpath('//news:title/text()', namespaces=self.namespace).getall()
        if self.start_date is not None and self.end_date is not None:
            for article, date,title in zip(article_urls, published_date, title):
                print(date)
                if self.start_date <= datetime.strptime(date.split('T')[0], '%Y-%m-%d') <= self.end_date:
                    article = {
                        "link": article,
                        "title": title,
                    }
                    self.articles.append(article)
        
        elif self.start_date is None and self.end_date is None:
            for article, date,title in zip(article_urls, published_date, title):
                if date == datetime.today().strftime("%Y-%m-%d"):
                    article = {
                        "link": article,
                        "title": title,
                    }
                    self.articles.append(article)

        elif self.start_date is None or self.end_date is None:
            raise ValueError("start_date and end_date both required.")            
        else:
            raise ValueError("Invalid date range")


    def parse_sitemap_article(self, response):
        title = response.css('#top > header > h1::text').getall()
        if title:
            article = {
                "link": response.url,
                "title": title,
            }
            self.articles.append(article)


    def parse_article(self, response):
        title = response.css('header.article_header > h1::text').getall()
        img_url = response.css("div.width_full >figure > div.pos_rel > img::attr('src')").getall()
        img_caption =  response.css('div.width_full >figure > figcaption > span::text').getall()
        article_author_url = response.css('a.author_link::attr(href)').getall()
        video_link = response.css('iframe.dailymotion-player::attr(src)').getall()
        text = response.css('section.content > p::text').getall()
        category = response.css('div.breadcrumb > a::text').getall()

        json_data = "".join(response.css('script[type="application/ld+json"]::text').getall())
   
        json_data = json.loads(json_data)
        
        article = { 
                    'raw_response':{
                        "content_type": response.headers.get("Content-Type").decode("utf-8"),
                        "content": response.text,
                    },
                    "parsed_json": {
                        "main":{
                            "@context": json_data[1]["@context"],
                            "@type": json_data[1]["@type"],
                            "mainEntityOfPage": {
                                "@type": json_data[1]["mainEntityOfPage"]["@type"],
                                "@id": json_data[1]["mainEntityOfPage"]["@id"]
                            },
                            "headline": json_data[1]['headline'],
                            "alternativeHeadline":json_data[1]['alternativeHeadline'],
                            "dateModified":json_data[1]['dateModified'],
                            "datePublished":json_data[1]['datePublished'],
                            "description": json_data[1]['description'],
                            "author": 
                                {
                                    "@type": json_data[1]['author'][0]["@type"],
                                    "name":json_data[1]['author'][0]["name"],
                                    
                                }
                            ,

                            "publisher": {'@type':json_data[1]['publisher']['@type'],
                                          "@id":json_data[2]["url"],
                                          'name':json_data[1]['publisher']['name'],
                                          'logo':{'@type':json_data[1]['publisher']['logo']['@type'],
                                                  'url':json_data[1]['publisher']['logo']['url'],
                                                  'width':{'@type':"Distance",
                                                           "name":str(json_data[1]['publisher']['logo']['width'])+" Px"},
                                                  'heigt':{'@type':"Distance", 'name':str(json_data[1]['publisher']['logo']['height'])+" Px"}}},
                            
                            "image":json_data[1]["image"],

                        },
                        "misc":json_data
                    },
                    
                    "parsed_data": {
                        "author": [
                            {
                                "@type": json_data[1]['author'][0]["@type"],
                                "name":json_data[1]['author'][0]["name"],
                            }
                        ],
                        "description": [json_data[1]['description']],
                        "modified_at":[json_data[1]['dateModified']],
                        "published_at": [json_data[1]['datePublished']],
        
                        "publisher": [{'@type':json_data[1]['publisher']['@type'], 'name':json_data[1]['publisher']['name'], 'logo':{'@type':json_data[1]['publisher']['logo']['@type'], 'url':json_data[1]['publisher']['logo']['url'], 'width':{'@type':"Distance", "name":str(json_data[1]['publisher']['logo']['width'])+" Px"}, 'heigt':{'@type':"Distance", 'name':str(json_data[1]['publisher']['logo']['height'])+" Px"}}}],

                        "text": text,
                        "thumbnail_image": [json_data[2]["url"]+img_url[0][1:]], #need to look it 
                        "title": title,
                        "images": [{'link': json_data[2]["url"]+img_url[0][1:], 'caption': img_caption[0]}],
                        
                        "section": "".join(category).split(","),
                        "tag":json_data[1]["keywords"]
                        }
                }
        if article_author_url:

            article['parsed_json']['main']['author']['url'] = json_data[2]["url"]+article_author_url[0][1:]
            article['parsed_data']['author'][0]['url'] = json_data[2]["url"]+article_author_url[0][1:]

        if video_link:
            article['parsed_data']['embed_video_link'] = [video_link]        
        self.articles.append(article)

        try:
            article['parse_json']['main']['isPartOf'] = json_data[1]["isPartOf"]
            article['parse_json']['main']["isAccessibleForFree"] = json_data[1]["isAccessibleForFree"]
        except:
            pass   
         
    def closed(self, reason):
        if self.type == "sitemap":
            filename = f'leparisien-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        elif self.type == "article":
            filename = f'leparisien-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.json'
        with open(f'{filename}.json', 'w') as f:
            json.dump(self.articles, f, indent=4)
[{"@context":"https://schema.org/","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"item":{"@id":"https://www.leparisien.fr/faits-divers/","name":"Faits-divers"}}]},{"@context":"https://schema.org","@type":"NewsArticle","mainEntityOfPage":{"@type":"WebPage","@id":"https://www.leparisien.fr/faits-divers/corse-des-nationalistes-occupent-le-tribunal-administratif-toute-la-journee-15-03-2023-G2MYKHYTDZDX5O2TPNG4HGMR7I.php"},"headline":"Corse : des nationalistes occupent le tribunal administratif toute la journée","alternativeHeadline":"Ils dénonçaient la décision du tribunal administratif établissant que l’usage de la langue corse dans les débats à l’Assemblée de Corse était contraire à la Constitution..","description":"Ils dénonçaient la décision du tribunal administratif établissant que l’usage de la langue corse dans les débats à l’Assemblée de Corse était contraire à la Constitution..","dateModified":"2023-03-15T22:07:55.935Z","datePublished":"2023-03-15T22:07:55Z","keywords":["faits-divers","Tribunal","Corse"],"articleSection":"faits-divers","author":[{"@type":"Person","name":"Le Parisien avec AFP","jobTitle":"Author","address":"Paris"}],"publisher":{"@type":"Organization","name":"Le Parisien","logo":{"@type":"ImageObject","url":"https://leparisien.fr/resizer/hsVGYq63d0ZhMeno4G34OjosBYk=/192x60/www.leparisien.fr/pf/resources/images/E-LOGO-LP-192x60.png%3Fd=507","height":60,"width":192}},"image":{"@type":"ImageObject","url":"https://leparisien.fr/resizer/tXQjkGWhgZ7PIuV0h9dNkkpHQ4w=/1200x675/cloudfront-eu-central-1.images.arcpublishing.com/leparisien/JHWY63BMSJBCZK7RZNIZHJD7DI.jpg","height":675,"width":1200},"speakable":{"@type":"SpeakableSpecification","xpath":["/html/headf/meta[@property='og:title']/@content","/html/head/meta[@name='description']/@content"],"url":"https://www.leparisien.fr/faits-divers/corse-des-nationalistes-occupent-le-tribunal-administratif-toute-la-journee-15-03-2023-G2MYKHYTDZDX5O2TPNG4HGMR7I.php"}},{"@context":"https://schema.org","@type":"WebSite","name":"Le Parisien","alternateName":"Actualités en Direct et info en continu sur Le Parisien","url":"https://www.leparisien.fr/","image":"https://www.leparisien.fr/pf/resources/images/E-LOGO-LP-192x60.png?d=507"}]