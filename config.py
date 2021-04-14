import os
from jinja2 import Environment, PackageLoader, select_autoescape

DIRECTORY_NAME = os.path.basename(os.path.dirname(os.path.realpath(__file__)))
TEMPLATES_DIRECTORY = 'templates'
JINJA_ENV = Environment(loader=PackageLoader(DIRECTORY_NAME, TEMPLATES_DIRECTORY), autoescape=select_autoescape(['html']))
BOT_TOKEN = '1773461202:AAEDdt2xNs-7C1zfIOOxLrVeeJl6nu5AeMY'
CHAT_NAME = '@test_channel53453'


