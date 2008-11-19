from scrapy.command import ScrapyCommand
from scrapy.fetcher import fetch
from scrapy.http import Request
from scrapy.item import ScrapedItem
from scrapy.spider import spiders
from scrapy.utils import display

class Command(ScrapyCommand):
    def syntax(self):
        return "[options] <url>"

    def short_desc(self):
        return "Parse the URL and print their results"

    def add_options(self, parser):
        ScrapyCommand.add_options(self, parser)
        parser.add_option("--links", dest="links", action="store_true", help="show extracted links")
        parser.add_option("--noitems", dest="noitems", action="store_true", help="don't show scraped items")
        parser.add_option("--identify", dest="identify", action="store_true", help="try to use identify instead of parse")
        parser.add_option("--nocolour", dest="nocolour", action="store_true", help="avoid using pygments to colorize the output")

    def pipeline_process(self, item, opts):
        return item

    def run(self, args, opts):
        if not args:
            print "A URL is required"
            return

        responses = fetch([args[0]])
        if responses:
            response = responses[0]
            spider = spiders.fromurl(response.url)
            if opts.identify:
                result = spider.identify_products(response)
            elif hasattr(spider, 'parse_url'):
                result = spider.parse_url(response)
            else:
                result = spider.parse(response)

            items = [self.pipeline_process(i, opts) for i in result if isinstance(i, ScrapedItem)]
            links = [i for i in result if isinstance(i, Request)]

            display.nocolour = opts.nocolour
            if not opts.noitems:
                print "# Scraped Items", "-"*60
                display.pprint(items)

            if opts.links:
                print "# Links", "-"*68
                display.pprint(links)

