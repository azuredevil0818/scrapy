from scrapy.utils.misc import load_object
from .config import Config

def get_application():
    config = Config()
    apppath = config.get('application', 'scrapyd.app.application')
    appfunc = load_object(apppath)
    return appfunc()
