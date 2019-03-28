"""
Some spiders used for testing and benchmarking
"""

import time
from six.moves.urllib.parse import urlencode

from scrapy.spiders import Spider
from scrapy.http import Request
from scrapy.item import Item
from scrapy.linkextractors import LinkExtractor


class MockServerSpider(Spider):
    def __init__(self, mockserver=None, *args, **kwargs):
        super(MockServerSpider, self).__init__(*args, **kwargs)
        self.mockserver = mockserver

class MetaSpider(MockServerSpider):

    name = 'meta'

    def __init__(self, *args, **kwargs):
        super(MetaSpider, self).__init__(*args, **kwargs)
        self.meta = {}

    def closed(self, reason):
        self.meta['close_reason'] = reason


class KeywordArgumentsSpider(MockServerSpider):

    name = 'kwargs'
    checks = list()

    def start_requests(self):
        data = {'key': 'value', 'number': 123}
        yield Request(self.mockserver.url('/first'), self.parse_first, cb_kwargs=data)
        yield Request(self.mockserver.url('/general_with'), self.parse_general, cb_kwargs=data)
        yield Request(self.mockserver.url('/general_without'), self.parse_general)
        yield Request(self.mockserver.url('/no_kwargs'), self.parse_no_kwargs)
        yield Request(self.mockserver.url('/default'), self.parse_default, cb_kwargs=data)
        yield Request(self.mockserver.url('/takes_less'), self.parse_takes_less, cb_kwargs=data)
        yield Request(self.mockserver.url('/takes_more'), self.parse_takes_more, cb_kwargs=data)

    def parse_first(self, response, key, number):
        self.checks.append(key == 'value')
        self.checks.append(number == 123)
        self.crawler.stats.inc_value('boolean_checks', 2)
        yield response.follow(
            self.mockserver.url('/two'),
            self.parse_second,
            cb_kwargs={'new_key': 'new_value'})

    def parse_second(self, response, new_key):
        self.checks.append(new_key == 'new_value')
        self.crawler.stats.inc_value('boolean_checks')

    def parse_general(self, response, **kwargs):
        if response.url.endswith('/general_with'):
            self.checks.append(kwargs['key'] == 'value')
            self.checks.append(kwargs['number'] == 123)
            self.crawler.stats.inc_value('boolean_checks', 2)
        elif response.url.endswith('/general_without'):
            self.checks.append(kwargs == {})
            self.crawler.stats.inc_value('boolean_checks')

    def parse_no_kwargs(self, response):
        self.checks.append(response.url.endswith('/no_kwargs'))
        self.crawler.stats.inc_value('boolean_checks')

    def parse_default(self, response, key, number=None, default=99):
        self.checks.append(response.url.endswith('/default'))
        self.checks.append(key == 'value')
        self.checks.append(number == 123)
        self.checks.append(default == 99)
        self.crawler.stats.inc_value('boolean_checks', 4)

    def parse_takes_less(self, response, key):
        """
        Should raise
        TypeError: parse_takes_less() got an unexpected keyword argument 'number'
        """

    def parse_takes_more(self, response, key, number, other):
        """
        Should raise
        TypeError: parse_takes_more() missing 1 required positional argument: 'other'
        """


class FollowAllSpider(MetaSpider):

    name = 'follow'
    link_extractor = LinkExtractor()

    def __init__(self, total=10, show=20, order="rand", maxlatency=0.0, *args, **kwargs):
        super(FollowAllSpider, self).__init__(*args, **kwargs)
        self.urls_visited = []
        self.times = []
        qargs = {'total': total, 'show': show, 'order': order, 'maxlatency': maxlatency}
        url = self.mockserver.url("/follow?%s" % urlencode(qargs, doseq=1))
        self.start_urls = [url]

    def parse(self, response):
        self.urls_visited.append(response.url)
        self.times.append(time.time())
        for link in self.link_extractor.extract_links(response):
            yield Request(link.url, callback=self.parse)


class DelaySpider(MetaSpider):

    name = 'delay'

    def __init__(self, n=1, b=0, *args, **kwargs):
        super(DelaySpider, self).__init__(*args, **kwargs)
        self.n = n
        self.b = b
        self.t1 = self.t2 = self.t2_err = 0

    def start_requests(self):
        self.t1 = time.time()
        url = self.mockserver.url("/delay?n=%s&b=%s" % (self.n, self.b))
        yield Request(url, callback=self.parse, errback=self.errback)

    def parse(self, response):
        self.t2 = time.time()

    def errback(self, failure):
        self.t2_err = time.time()


class SimpleSpider(MetaSpider):

    name = 'simple'

    def __init__(self, url="http://localhost:8998", *args, **kwargs):
        super(SimpleSpider, self).__init__(*args, **kwargs)
        self.start_urls = [url]

    def parse(self, response):
        self.logger.info("Got response %d" % response.status)


class ItemSpider(FollowAllSpider):

    name = 'item'

    def parse(self, response):
        for request in super(ItemSpider, self).parse(response):
            yield request
            yield Item()
            yield {}


class DefaultError(Exception):
    pass


class ErrorSpider(FollowAllSpider):

    name = 'error'
    exception_cls = DefaultError

    def raise_exception(self):
        raise self.exception_cls('Expected exception')

    def parse(self, response):
        for request in super(ErrorSpider, self).parse(response):
            yield request
            self.raise_exception()


class BrokenStartRequestsSpider(FollowAllSpider):

    fail_before_yield = False
    fail_yielding = False

    def __init__(self, *a, **kw):
        super(BrokenStartRequestsSpider, self).__init__(*a, **kw)
        self.seedsseen = []

    def start_requests(self):
        if self.fail_before_yield:
            1 / 0

        for s in range(100):
            qargs = {'total': 10, 'seed': s}
            url = self.mockserver.url("/follow?%s") % urlencode(qargs, doseq=1)
            yield Request(url, meta={'seed': s})
            if self.fail_yielding:
                2 / 0

        assert self.seedsseen, \
                'All start requests consumed before any download happened'

    def parse(self, response):
        self.seedsseen.append(response.meta.get('seed'))
        for req in super(BrokenStartRequestsSpider, self).parse(response):
            yield req


class SingleRequestSpider(MetaSpider):

    seed = None
    callback_func = None
    errback_func = None

    def start_requests(self):
        if isinstance(self.seed, Request):
            yield self.seed.replace(callback=self.parse, errback=self.on_error)
        else:
            yield Request(self.seed, callback=self.parse, errback=self.on_error)

    def parse(self, response):
        self.meta.setdefault('responses', []).append(response)
        if callable(self.callback_func):
            return self.callback_func(response)
        if 'next' in response.meta:
            return response.meta['next']

    def on_error(self, failure):
        self.meta['failure'] = failure
        if callable(self.errback_func):
            return self.errback_func(failure)


class DuplicateStartRequestsSpider(MockServerSpider):
    dont_filter = True
    name = 'duplicatestartrequests'
    distinct_urls = 2
    dupe_factor = 3

    def start_requests(self):
        for i in range(0, self.distinct_urls):
            for j in range(0, self.dupe_factor):
                url = self.mockserver.url("/echo?headers=1&body=test%d" % i)
                yield Request(url, dont_filter=self.dont_filter)

    def __init__(self, url="http://localhost:8998", *args, **kwargs):
        super(DuplicateStartRequestsSpider, self).__init__(*args, **kwargs)
        self.visited = 0

    def parse(self, response):
        self.visited += 1
