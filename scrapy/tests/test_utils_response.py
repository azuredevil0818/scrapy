import unittest
from scrapy.http import Response, TextResponse
from scrapy.utils.response import body_or_str, get_base_url, get_meta_refresh, response_httprepr

class ResponseUtilsTest(unittest.TestCase):
    dummy_response = TextResponse(url='http://example.org/', body='dummy_response')

    def test_body_or_str_input(self):
        self.assertTrue(isinstance(body_or_str(self.dummy_response), basestring))
        self.assertTrue(isinstance(body_or_str('text'), basestring))
        self.assertRaises(Exception, body_or_str, 2)

    def test_body_or_str_extraction(self):
        self.assertEqual(body_or_str(self.dummy_response), 'dummy_response')
        self.assertEqual(body_or_str('text'), 'text')

    def test_body_or_str_encoding(self):
        self.assertTrue(isinstance(body_or_str(self.dummy_response, unicode=False), str))
        self.assertTrue(isinstance(body_or_str(self.dummy_response, unicode=True), unicode))

        self.assertTrue(isinstance(body_or_str('text', unicode=False), str))
        self.assertTrue(isinstance(body_or_str('text', unicode=True), unicode))

        self.assertTrue(isinstance(body_or_str(u'text', unicode=False), str))
        self.assertTrue(isinstance(body_or_str(u'text', unicode=True), unicode))

    def test_get_base_url(self):
        response = Response(url='http://example.org', body="""\
            <html>\
            <head><title>Dummy</title><base href='http://example.org/something' /></head>\
            <body>blahablsdfsal&amp;</body>\
            </html>""")
        self.assertEqual(get_base_url(response), 'http://example.org/something')

    def test_get_meta_refresh(self):
        body = """
            <html>
            <head><title>Dummy</title><meta http-equiv="refresh" content="5;url=http://example.org/newpage" /></head>
            <body>blahablsdfsal&amp;</body>
            </html>"""
        response = Response(url='http://example.org', body=body)
        self.assertEqual(get_meta_refresh(response), ('5', 'http://example.org/newpage'))

        # refresh without url should return (None, None)
        body = """<meta http-equiv="refresh" content="5" />"""
        response = Response(url='http://example.org', body=body)
        self.assertEqual(get_meta_refresh(response), (None, None))

        body = """<meta http-equiv="refresh" content="5;
            url=http://example.org/newpage" /></head>"""
        response = Response(url='http://example.org', body=body)
        self.assertEqual(get_meta_refresh(response), ('5', 'http://example.org/newpage'))

    def test_response_httprepr(self):
        r1 = Response("http://www.example.com")
        self.assertEqual(response_httprepr(r1), 'HTTP/1.1 200 OK\r\n\r\n')

        r1 = Response("http://www.example.com", status=404, headers={"Content-type": "text/html"}, body="Some body")
        self.assertEqual(response_httprepr(r1), 'HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\nSome body')


if __name__ == "__main__":
    unittest.main()
