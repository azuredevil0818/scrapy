# -*- coding: utf8 -*-
import os
import unittest
import re

from scrapy.item.adaptors import AdaptorPipe
from scrapy.contrib import adaptors
from scrapy.http import Response, Headers
from scrapy.xpath.selector import HtmlXPathSelector, XmlXPathSelector

class AdaptorPipeTestCase(unittest.TestCase):
    def test_pipe_init(self):
        self.assertRaises(TypeError, AdaptorPipe, [adaptors.extract, 'a string'])

    def test_adaptor_args(self):
        def sample_adaptor(value, adaptor_args):
            '''Dummy adaptor that joins the received value with the given string'''
            sample_text = adaptor_args.get('sample_arg', 'sample text 1')
            return '%s "%s"' % (value, sample_text)

        sample_value = 'hi, this is my text:'
        sample_pipe = AdaptorPipe([sample_adaptor])
        self.assertEqual(sample_pipe(sample_value), 'hi, this is my text: "sample text 1"')
        self.assertEqual(sample_pipe(sample_value, sample_arg='foobarfoobar'),
            'hi, this is my text: "foobarfoobar"')

    def test_add(self):
        pipe1 = AdaptorPipe([adaptors.extract])
        pipe2 = [adaptors.remove_tags]
        pipe3 = (adaptors.remove_root, )
        sample_callable = dir

        self.assertTrue(isinstance(pipe1 + pipe1, AdaptorPipe))
        self.assertTrue(isinstance(pipe1 + pipe2, AdaptorPipe))
        self.assertTrue(isinstance(pipe1 + pipe3, AdaptorPipe))
        self.assertTrue(isinstance(pipe1 + sample_callable, AdaptorPipe))

class AdaptorsTestCase(unittest.TestCase):
    def setUp(self):
        self.samplesdir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'sample_data', 'adaptors'))

    def get_selector(self, domain, url, sample_filename, headers=None, selector=HtmlXPathSelector):
        sample_filename = os.path.join(self.samplesdir, sample_filename)
        body = file(sample_filename).read()
        response = Response(url=url, headers=Headers(headers), status=200, body=body)
        return selector(response)

    def test_extract(self):
        def check_extractor(x, pound=True, euro=True):
            poundre = re.compile(r'<span class="pound" .*?>(.*?)</span>')
            eurore = re.compile(r'<span class="euro" .*?>(.*?)</span>')

            if pound:
                self.assertEqual(adaptors.extract(x.x("//span[@class='pound']/text()")), [u'\xa3'])
                self.assertEqual(adaptors.extract(x.x("//span[@class='pound']/@value")), [u'\xa3'])
                self.assertEqual(adaptors.extract(x.re(poundre)), [u'\xa3'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='poundent']/text()")), [u'\xa3'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='poundent']/@value")), [u'\xa3'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='poundnum']/text()")), [u'\xa3'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='poundnum']/@value")), [u'\xa3'])
            if euro:
                self.assertEqual(adaptors.extract(x.x("//span[@class='euro']/text()")), [u'\u20ac'])
                self.assertEqual(adaptors.extract(x.x("//span[@class='euro']/@value")), [u'\u20ac'])
                self.assertEqual(adaptors.extract(x.re(eurore)), [u'\u20ac'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='euroent']/text()")), [u'\u20ac'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='euroent']/@value")), [u'\u20ac'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='euronum']/text()")), [u'\u20ac'])
            self.assertEqual(adaptors.extract(x.x("//span[@class='euronum']/@value")), [u'\u20ac'])

        x = self.get_selector('example.com',
                         'http://www.example.com/test/utf8',
                         'enc-utf8.html',
                         {})
        check_extractor(x)

        x = self.get_selector('example.com',
                         'http://www.example.com/test/latin1',
                         'enc-latin1.html',
                         {})
        check_extractor(x, euro=False)

        x = self.get_selector('example.com',
                         'http://www.example.com/test/cp1252',
                         'enc-cp1252.html',
                         {})
        check_extractor(x)

        # HTTP utf-8 | Meta latin1 | Content ascii | using entities
        x = self.get_selector('example.com',
                         'http://www.example.com/test/ascii',
                         'enc-ascii.html',
                         {'Content-Type': ['text/html; charset=utf-8']})
        check_extractor(x, pound=False, euro=False)

        # Test for inconsistencies between HTTP header encoding and 
        # META header encoding. It must prefer HTTP header like browsers do
        x = self.get_selector('example.com',
                         'http://www.example.com/test/utf8-meta-latin1',
                         'enc-utf8-meta-latin1.html',
                         {'Content-Type': ['text/html; charset=utf-8']})
        check_extractor(x)


    def test_extract_unquoted(self):
        x = self.get_selector('example.com', 'http://www.example.com/test_unquoted', 'extr_unquoted.xml', selector=XmlXPathSelector)

        # test unquoting
        self.assertEqual(adaptors.extract(x.x('//tag1/text()')), [u'test text & &', u'more test text &amp; &gt;', u'blah&blah'])
        self.assertEqual(adaptors.extract(x.x('//tag2/text()')), [u'blaheawfds<'])

        # test without unquoting
        self.assertEqual(adaptors.extract(x.x('//tag1/text()'), {'use_unquote': False}),
            [u'test text &amp; &amp;', u'<![CDATA[more test text &amp; &gt;]]>', u'blah&amp;blah'])
        self.assertEqual(adaptors.extract(x.x('//tag2/text()'), {'use_unquote': False}), [u'blaheawfds&lt;'])

    def test_extract_links(self):
        test_data = """<html><body>
                         <div>
                           <a href="lala1/lala1.html">lala1</a>
                           <a href="/lala2.html">lala2</a>
                           <a href="http://foobar.com/pepepe/papapa/lala3.html">lala3</a>
                           <a href="lala4.html"><img src="/imgs/lala4.jpg" /></a>
                           <a onclick="javascript: opensomething('/my_html1.html');">something1</a>
                           <a onclick="javascript: opensomething('dummy/my_html2.html');">something2</a>
                         </div>
                       </body></html>"""
        sample_response = Response('http://foobar.com/dummy', body=test_data)
        sample_xsel = XmlXPathSelector(sample_response)
        sample_adaptor = adaptors.ExtractImages(response=sample_response)

        self.assertEqual(sample_adaptor(None), [])
        self.assertEqual(sample_adaptor([]), [])
        self.assertEqual(sample_adaptor('http://foobar.com/my_image.jpg'), ['http://foobar.com/my_image.jpg'])
        self.assertEqual(sample_adaptor([sample_xsel.x('//@href'), 'my_image.gif']),
                         [u'http://foobar.com/lala1/lala1.html', u'http://foobar.com/lala2.html',
                          u'http://foobar.com/pepepe/papapa/lala3.html', u'http://foobar.com/lala4.html', u'http://foobar.com/my_image.gif'])
        self.assertEqual(sample_adaptor(sample_xsel.x('//a')),
                         [u'http://foobar.com/lala1/lala1.html', u'http://foobar.com/lala2.html',
                          u'http://foobar.com/pepepe/papapa/lala3.html', u'http://foobar.com/imgs/lala4.jpg'])
        self.assertEqual(sample_adaptor(sample_xsel.x('//a[@onclick]').re(r'opensomething\(\'(.*?)\'\)')),
                         [u'http://foobar.com/my_html1.html', u'http://foobar.com/dummy/my_html2.html'])


    def test_to_unicode(self):
        self.assertEqual(adaptors.to_unicode(['lala', 'lele', 'lulu\xc3\xb1', 1, '\xc3\xa1\xc3\xa9']),
                         [u'lala', u'lele', u'lulu\xf1', u'1', u'\xe1\xe9'])


    def test_regex(self):
        adaptor = adaptors.Regex(regex=r'href="(.*?)"')
        self.assertEqual(adaptor(['<a href="lala.com">dsa</a><a href="pepe.co.uk"></a>',
                                  '<a href="das.biz">href="lelelel.net"</a>']),
                                  ['lala.com', 'pepe.co.uk', 'das.biz', 'lelelel.net'])


    def test_unquote_all(self):
        self.assertEqual(adaptors.Unquote()([u'hello&copy;&amp;welcome', u'&lt;br /&gt;&amp;']), [u'hello\xa9&welcome', u'<br />&'])


    def test_unquote(self):
        self.assertEqual(adaptors.Unquote(keep=['amp', 'lt'])([u'hello&copy;&amp;welcome', u'&lt;br /&gt;&amp;']), [u'hello\xa9&amp;welcome', u'&lt;br />&amp;'])


    def test_remove_tags(self):
        test_data = ['<a href="lala">adsaas<br /></a>', '<div id="1"><table>dsadasf</table></div>']
        self.assertEqual(adaptors.remove_tags(test_data), ['adsaas', 'dsadasf'])


    def test_remove_root(self):
        self.assertEqual(adaptors.remove_root(['<div>lallaa<a href="coso">dsfsdfds</a>pepepep<br /></div>']),
                         ['lallaa<a href="coso">dsfsdfds</a>pepepep<br />'])


    def test_remove_multispaces(self):
        self.assertEqual(adaptors.clean_spaces(['  hello,  whats     up?', 'testing testingtesting      testing']),
                         [' hello, whats up?', 'testing testingtesting testing'])


    def test_strip(self):
        self.assertEqual(adaptors.strip([' hi there, sweety ;D ', ' I CAN HAZ TEST??    ']),
                         ['hi there, sweety ;D', 'I CAN HAZ TEST??'])
        self.assertEqual(adaptors.strip('      hello there, this is my test     '),
                         'hello there, this is my test')


    def test_drop_empty_elements(self):
        self.assertEqual(adaptors.drop_empty([1, 2, None, 5, 0, 6, False, 'hi']),
                         [1, 2, 5, 6, 'hi'])


    def test_delist(self):
        self.assertEqual(adaptors.Delist()(['hi', 'there', 'fellas.', 'this', 'is', 'my', 'test.']),
                         'hi there fellas. this is my test.')


