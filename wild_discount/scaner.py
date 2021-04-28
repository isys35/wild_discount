import requests
from bs4 import BeautifulSoup
import json
import time
import os
from jinja2 import Template

from .config import BASE_DIR

from telebot.apihelper import ApiTelegramException
import re

from wild_discount.db import Category, DBManager
from wild_discount import bot

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

HOST = 'https://www.wildberries.ru'
DELAY = 3


class TemplateMessage:
    TEMPLATE_FILE = 'message.html'
    TEMPLATE_DIR = 'templates'
    TEMPLATE_PATH = os.path.join(BASE_DIR, TEMPLATE_DIR, TEMPLATE_FILE)

    def __init__(self, data: dict):
        self.data = data

    def get_text(self):
        with open(self.TEMPLATE_PATH, 'r', encoding='utf-8') as template_file:
            template_text = template_file.read()
        template = Template(template_text)
        text_message = template.render(self.data)
        return text_message


class ParserProduct:
    def __init__(self):
        self.response_text = None

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

    def _get_other_colors(self):
        soup = BeautifulSoup(self.response_text, 'lxml')
        urls = []
        all_color = soup.select('.swiper-slide.color.j-color')
        if all_color:
            for el in all_color[1:]:
                url = 'https://www.wildberries.ru' + el.select_one('a')['href'].replace('?targetUrl=EX', '')
                urls.append(url)
        return urls

    def get_photo_url(self, response_text):
        self.response_text = response_text
        soup = BeautifulSoup(self.response_text, 'lxml')
        photo_url = 'https:' + soup.select_one('img.preview-photo.j-zoom-preview')['src']
        return photo_url

    def get_data(self, response_text):
        self.response_text = response_text
        re_search = re.search(r'\"priceForProduct\":(\{.+?\})', self.response_text)
        if re_search:
            json_price = json.loads(re_search.group(1))
            discount = json_price.get('sale')
            price = json_price.get('priceWithSale')
            old_price = json_price.get('price')
            name = self._get_name()
            brand = self._get_brand()
            aviable = self._get_aviable()
            other_colors = self._get_other_colors()
            data = {'discount': discount,
                    'price': price,
                    'name': name,
                    'brand': brand,
                    'aviable': aviable,
                    'old_price': old_price,
                    'other_colors': other_colors}
            print(data)
            self.response_text = None
            return data
        self.response_text = None


class ProductFilter:
    EXCEPTION_MARKETS = ['Шепелев']

    def __init__(self, product_block: BeautifulSoup, discount: int,
                 price_border_with_discount: int, price_border: int):
        self.product_block = product_block
        self.discount = discount
        self.price_border_with_discount = price_border_with_discount
        self.price_border = price_border

    def get_url(self):
        url = HOST + self.product_block.select_one('.ref_goods_n_p.j-open-full-product-card')['href']
        return url

    def _is_product_in_db(self):
        url = self.get_url()
        product_from_db = DBManager().product.get_by_url(url)
        if product_from_db:
            return True

    def _is_product_has_sale_block(self):
        sale_block = self.product_block.select_one('span.price-sale.active')
        if sale_block:
            return True

    def _is_product_brand_in_exceptions(self):
        brand = self.product_block.select_one('.brand-name.c-text-sm').text.replace('/', '').strip()
        if brand in self.EXCEPTION_MARKETS:
            return True

    def _is_product_discount_match(self):
        sale_block = self.product_block.select_one('span.price-sale.active')
        product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
        if product_discount >= self.discount:
            return True

    def _is_product_price_in_border_price(self):
        sale_block = self.product_block.select_one('span.price-sale.active')
        product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
        product_old_price = int(
            ''.join(re.findall(r'\d', self.product_block.select_one('span.price-old-block').select_one('del').text)))
        product_new_price = int(''.join(re.findall(r'\d', self.product_block.select_one('ins.lower-price').text)))
        filter_price = product_discount >= self.discount and \
                       product_old_price < self.price_border and \
                       product_new_price < self.price_border_with_discount
        if filter_price:
            return True

    def check(self):
        if self._is_product_in_db():
            return
        if not self._is_product_has_sale_block():
            return
        if self._is_product_brand_in_exceptions():
            return
        if not self.price_border and not self.price_border_with_discount:
            if self._is_product_discount_match():
                return True
        else:
            if self._is_product_price_in_border_price():
                return True


class ParserCategory:

    def __init__(self, category: Category):
        self.response_text = None
        self.category = category

    @staticmethod
    def get_products_blocks(response_text):
        soup = BeautifulSoup(response_text, 'lxml')
        products_blocks = soup.select('.dtList.i-dtList.j-card-item ')
        return products_blocks

    def get_urls_products(self, response_text):
        self.response_text = response_text
        products_blocks = self.get_products_blocks(response_text)
        urls = []
        for product_block in products_blocks:
            product_filter = ProductFilter(product_block, discount=self.category.discount,
                                           price_border=self.category.price_border,
                                           price_border_with_discount=self.category.price_border_with_discount)
            if product_filter.check():
                url = product_filter.get_url()
                urls.append(url)
        self.response_text = None
        return urls

    def get_next_page(self, response_text):
        soup = BeautifulSoup(response_text, 'lxml')
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
        self.depth = None

    def _update_url(self, url):
        if not url:
            if 'xsubject' in self.category.url:
                url = self.category.url + '&sort=sale'
            else:
                url = self.category.url + '?sort=sale'
        else:
            url = url + '&sort=sale'
        return url

    @staticmethod
    def _get_page_from_url(url):
        re_search_page = re.search(r'page=(\d+)', url)
        if re_search_page:
            page = int(re_search_page.group(1))
            return page

    def get(self, url=None):
        url = self._update_url(url)
        page = self._get_page_from_url(url)
        if self.depth and page and page > self.depth:
            return
        response = requests.get(url)
        parser = ParserCategory(self.category)
        products_urls = parser.get_urls_products(response.text)
        next_page_url = parser.get_next_page(response.text)
        response = None
        for product_url in products_urls:
            yield product_url
        if next_page_url:
            products_page_urls = self.get(next_page_url)
            for product_page_url in products_page_urls:
                yield product_page_url


def update_products_in_db():
    print('[INFO] Обновление продуктов в бд')
    products = DBManager().product.get_opened()
    for product in products:
        response_product = requests.get(product.url)
        telegram_message = DBManager().telegram_message.get_with_product(product)
        if not telegram_message:
            continue
        product_data = ParserProduct().get_data(response_product.text)
        if not product_data:
            continue
        if product_data['aviable'] != product.aviable:
            if product_data['price'] == 0:
                product_data['aviable'] = 0
            if product_data['aviable'] == 0:
                product.closed = True
            product_data['url'] = product.url
            new_text_message = TemplateMessage(product_data).get_text()
            try:
                bot.change_post(telegram_message.tg_id, new_text_message)
            except ApiTelegramException:
                print(ApiTelegramException)
                continue
            telegram_message.text = new_text_message
            DBManager().product.save(product)
            DBManager().telegram_message.save(telegram_message)
            time.sleep(DELAY)


def update_from_generators(generators: list):
    while generators:
        for el in generators:
            try:
                product_url = next(el[1])
            except StopIteration:
                del el
                continue
            category = el[0]
            product_in_db = DBManager().product.get_by_url(product_url)
            if product_in_db:
                continue
            response_product = requests.get(product_url)
            product_data = ParserProduct().get_data(response_product.text)
            if not product_data:
                continue
            if product_data['other_colors']:
                for other_color_url in product_data['other_colors']:
                    DBManager().product.create({'url': other_color_url, 'category':category})
            product_data['url'] = product_url
            text_message = TemplateMessage(product_data).get_text()
            photo_url = ParserProduct().get_photo_url(response_product.text)
            product_data['category'] = category
            product = DBManager().product.create(product_data)
            try:
                message_id = bot.send_post(photo_url, text_message)
            except ApiTelegramException:
                continue
            DBManager().telegram_message.create({'product': product, 'tg_id': message_id, 'text': text_message})
            time.sleep(DELAY)


def update_new_products():
    print('[INFO] Поиск новых продуктов')
    product_generator_list = []
    categories = DBManager().category.get_all()
    for category in categories:
        products_urls = GeneratorProductsURLS(category).get()
        product_generator_list.append((category, products_urls))
    update_from_generators(product_generator_list)


def update_new_products_with_depth_limit():
    product_generator_list = []
    categories = DBManager().category.get_all()
    for category in categories:
        products_urls_generator = GeneratorProductsURLS(category)
        products_urls_generator.depth = 10
        products_urls = products_urls_generator.get()
        product_generator_list.append((category, products_urls))
    update_from_generators(product_generator_list)


def update_products():
    update_products_in_db()
    update_new_products_with_depth_limit()
