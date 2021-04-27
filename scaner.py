import requests
from bs4 import BeautifulSoup
import re
import json
import time
import httplib2
import os
from jinja2 import Template
import traceback
from peewee import IntegrityError

from telebot.apihelper import ApiTelegramException

from db import Category, DBManager
import bot

MAIN_HEADERS = {
    'Host': 'www.wildberries.ru',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0',
    'Accept': '*/*',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'X-Requested-With': 'XMLHttpRequest',
    'Connection': 'keep-alive',
    'Referer': 'https://www.wildberries.ru/',
    'TE': 'Trailers'
}
URL_CATEGORIES = 'https://www.wildberries.ru/menu/getrendered?lang=ru&burger=true'

HOST = 'https://www.wildberries.ru'
DELAY = 3


def save_page(response: str, file_name='page.html'):
    with open(file_name, 'w', encoding='utf8') as html_file:
        html_file.write(response)


class TemplateMessage:
    TEMPLATE_FILE = 'template.html'
    TEMPLATE_DIR = 'templates'

    def __init__(self, data):
        self.data = data

    def get_text(self):
        template_path = os.path.join(self.TEMPLATE_DIR, self.TEMPLATE_FILE)
        with open(template_path, 'r', encoding='utf-8') as template_file:
            template_text = template_file.read()
        template = Template(template_text)
        text_message = template.render(self.data)
        return text_message


class ParserProduct:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def _get_description(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        description = soup.select_one('.description-text')
        if description:
            return description.select_one('p').text

    def _get_name(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        name = soup.select_one('span.name')
        if name:
            return name.text

    def _get_brand(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        brand = soup.select_one('span.brand')
        if brand:
            return brand.text

    def _get_aviable(self):
        return sum([int(el) for el in re.findall(r'"quantity":(\d+),', self.response_text)])

    def get_photo_url(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        return 'https:' + soup.select_one('img.preview-photo.j-zoom-preview')['src']

    def get_data(self):
        re_search = re.search(r'\"priceForProduct\":(\{.+?\})', self.response_text)
        if re_search:
            json_price = json.loads(re_search.group(1))
            discount = json_price.get('sale')
            price = json_price.get('priceWithSale')
            old_price = json_price.get('price')
            name = self._get_name()
            brand = self._get_brand()
            aviable = self._get_aviable()
            data = {'discount': discount,
                    'price': price,
                    'name': name,
                    'brand': brand,
                    'aviable': aviable,
                    'old_price': old_price}
            print(data)
            return data


class ParserCategory:
    EXCEPTION_MARKET_FILE = 'exceptions_markets.txt'
    with open(EXCEPTION_MARKET_FILE, 'r') as exc_market_file:
        EXCEPTION_MARKETS = exc_market_file.read().split('\n')

    def __init__(self, response_text: str, category: Category):
        self.response_text = response_text
        self.category = category

    @staticmethod
    def _get_url(product_block):
        url = HOST + product_block.select_one('.ref_goods_n_p.j-open-full-product-card')['href']
        return url

    def _check_product(self, product_block):
        url = self._get_url(product_block)
        product_from_db = DBManager().product.get_by_url(url)
        if product_from_db:
            return
        sale_block = product_block.select_one('span.price-sale.active')
        if not sale_block:
            return
        brand = product_block.select_one('.brand-name.c-text-sm').text.replace('/', '').strip()
        if brand in self.EXCEPTION_MARKETS:
            return
        product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
        if not self.category.price_border and not self.category.price_border_with_discount:
            if product_discount >= self.category.discount:
                return True
        else:
            product_old_price = int(
                ''.join(re.findall(r'\d', product_block.select_one('span.price-old-block').select_one('del').text)))
            product_new_price = int(''.join(re.findall(r'\d', product_block.select_one('ins.lower-price').text)))
            filter_price = product_discount >= self.category.discount and \
                           product_old_price < self.category.price_border and \
                           product_new_price < self.category.price_border_with_discount
            if filter_price:
                return True

    def get_urls_products(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        products_blocks = soup.select('.dtList.i-dtList.j-card-item ')
        urls = []
        for product_block in products_blocks:
            if self._check_product(product_block):
                url = self._get_url(product_block)
                urls.append(url)
        return urls

    def get_url_product(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        products_blocks = soup.select('.dtList.i-dtList.j-card-item ')
        for product_block in products_blocks:
            if self._check_product(product_block):
                url = self._get_url(product_block)
                return url

    def get_next_page(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        products_blocks = soup.select('.dtList.i-dtList.j-card-item.no-left-part')
        for product_block in products_blocks:
            sale_block = product_block.select_one('span.price-sale.active')
            if not sale_block:
                return
            else:
                product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
                if product_discount < self.category.discount:
                    return
        block_next_page = soup.select_one('.pagination-next')
        if block_next_page:
            return HOST + block_next_page['href']


class GeneratorProductsURLS:
    def __init__(self, category: Category):
        self.category = category

    def get(self, url=None):
        if not url:
            if 'xsubject' in self.category.url:
                url = self.category.url + '&sort=sale'
            else:
                url = self.category.url + '?sort=sale'
        else:
            url = url + '&sort=sale'
        response = requests.get(url)
        parser = ParserCategory(response.text, self.category)
        products_urls = parser.get_urls_products()
        next_page_url = parser.get_next_page()
        response = None
        parser.response_text = None
        for product_url in products_urls:
            yield product_url
        if next_page_url:
            products_page_urls = self.get(next_page_url)
            for product_page_url in products_page_urls:
                yield product_page_url


class GetterProductURl:
    def __init__(self, category: Category):
        self.category = category

    def get(self, url=None):
        if not url:
            if 'xsubject' in self.category.url:
                url = self.category.url + '&sort=sale'
            else:
                url = self.category.url + '?sort=sale'
        else:
            url = url + '&sort=sale'
        response = requests.get(url)
        parser = ParserCategory(response.text, self.category)
        product_url = parser.get_url_product()
        if product_url:
            return product_url
        next_page_url = parser.get_next_page()
        if next_page_url:
            response = None
            parser.response_text = None
            product_page_url = self.get(next_page_url)
            if product_page_url:
                return product_page_url


class ImageParser:
    IMG_DIRECTORY = 'images'

    def __init__(self, url):
        self.url = url
        self.path = os.path.join(self.IMG_DIRECTORY, self.url.split('/')[-1])

    def save(self):
        if not os.path.exists(self.IMG_DIRECTORY):
            os.makedirs(self.IMG_DIRECTORY)
        h = httplib2.Http('.cache')
        response, content = h.request(self.url)
        with open(self.path, 'wb') as img_file:
            img_file.write(content)

    def delete(self):
        os.remove(self.path)


def update_products_in_db():
    print('[INFO] Обновление продуктов в бд')
    products = DBManager().product.get_opened()
    for product in products:
        response_product = requests.get(product.url)
        product_data = ParserProduct(response_product.text).get_data()
        if not product_data:
            product.closed = True
            product_data = product.__dict__
            product_data['aviable'] = 0
            new_text_message = TemplateMessage(product_data).get_text()
            telegram_message = DBManager().telegram_message.get_with_product(product)
            try:
                bot.change_post(telegram_message.tg_id, new_text_message)
            except ApiTelegramException:
                print(ApiTelegramException)
                continue
            telegram_message.text = new_text_message
            DBManager().product.save(product)
            DBManager().telegram_message.save(telegram_message)
            time.sleep(DELAY)
            continue
        if product_data['aviable'] != product.aviable:
            if product_data['aviable'] == 0:
                product.closed = True
            product_data['url'] = product.url
            new_text_message = TemplateMessage(product_data).get_text()
            telegram_message = DBManager().telegram_message.get_with_product(product)
            try:
                bot.change_post(telegram_message.tg_id, new_text_message)
            except ApiTelegramException:
                print(ApiTelegramException)
                continue
            telegram_message.text = new_text_message
            DBManager().product.save(product)
            DBManager().telegram_message.save(telegram_message)
            time.sleep(DELAY)


def update_new_products():
    print('[INFO] Поиск новых продуктов')
    product_generator_list = []
    categories = DBManager().category.get_all()
    for category in categories:
        products_urls = GeneratorProductsURLS(category).get()
        product_generator_list.append((category, products_urls))
    while product_generator_list:
        for el in product_generator_list:
            try:
                product_url = next(el[1])
            except StopIteration:
                del el
                continue
            category = el[0]
            response_product = requests.get(product_url)
            product_data = ParserProduct(response_product.text).get_data()
            product_data['url'] = product_url
            text_message = TemplateMessage(product_data).get_text()
            photo_url = ParserProduct(response_product.text).get_photo_url()
            try:
                message_id = bot.send_post(photo_url, text_message)
            except ApiTelegramException:
                print(ApiTelegramException)
                continue
            product_data['category'] = category
            try:
                product = DBManager().product.create(product_data)
                DBManager().telegram_message.create({'product': product, 'tg_id': message_id, 'text': text_message})
            except IntegrityError:
                continue
            time.sleep(DELAY)


def update_new_products_without_generator():
    categories = DBManager().category.get_all()
    for category in categories:
        product_url = GetterProductURl(category).get()
        if product_url:
            response_product = requests.get(product_url)
            product_data = ParserProduct(response_product.text).get_data()
            product_data['url'] = product_url
            text_message = TemplateMessage(product_data).get_text()
            photo_url = ParserProduct(response_product.text).get_photo_url()
            try:
                message_id = bot.send_post(photo_url, text_message)
            except ApiTelegramException:
                print(ApiTelegramException)
                continue
            product_data['category'] = category
            product = DBManager().product.create(product_data)
            DBManager().telegram_message.create({'product': product, 'tg_id': message_id, 'text': text_message})
            time.sleep(DELAY)


def update_products():
    update_new_products()
    update_products_in_db()


if __name__ == '__main__':
    while True:
        try:
            update_products()
        except Exception:
            print(traceback.format_exc())
            break
