import requests
from bs4 import BeautifulSoup
import re
import json
import time
import httplib2
import os
from jinja2 import Template

from db import Category, Product, TelegramMessage, Photo
import config
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
IMG_DIRECTORY = 'images'
DELAY = 3
EXCEPTION_MARKET_FILE = 'exceptions_markets.txt'

with open(EXCEPTION_MARKET_FILE, 'r') as exc_market_file:
    EXCEPTION_MARKETS = exc_market_file.read().split('\n')

if not os.path.exists(IMG_DIRECTORY): os.makedirs(IMG_DIRECTORY)


def save_page(response: str, file_name='page.html'):
    with open(file_name, 'w', encoding='utf8') as html_file:
        html_file.write(response)


def parse_products_urls(response: str, category: Category):
    soup = BeautifulSoup(response, 'lxml')
    products_blocks = soup.select('.dtList.i-dtList.j-card-item ')
    # save_page(response)
    # sys.exit()
    for product_block in products_blocks:
        url = HOST + product_block.select_one('.ref_goods_n_p.j-open-full-product-card')['href']
        sale_block = product_block.select_one('span.price-sale.active')
        if sale_block:
            product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
            if product_discount >= category.discount:
                yield url


def parse_next_page(response: str, category: Category):
    soup = BeautifulSoup(response, 'lxml')
    products_blocks = soup.select('.dtList.i-dtList.j-card-item.no-left-part')
    for product_block in products_blocks:
        sale_block = product_block.select_one('span.price-sale.active')
        if not sale_block:
            return
        else:
            product_discount = int(sale_block.text.replace('-', '').replace('%', ''))
            if product_discount < category.discount:
                return
    block_next_page = soup.select_one('.pagination-next')
    if block_next_page:
        return HOST + block_next_page['href']


def get_products_url_from_category(category: Category):
    first_page_url = category.url + '?sort=sale'
    response = requests.get(first_page_url)
    products_urls = parse_products_urls(response.text, category)
    for product_url in products_urls:
        yield product_url
    next_page_url = parse_next_page(response.text, category)
    if next_page_url:
        products_page_urls = get_products_url_from_category_page(next_page_url, category)
        for product_page_url in products_page_urls:
            yield product_page_url


def get_products_url_from_category_page(url: str, category: Category):
    url = url + '&sort=sale'
    response = requests.get(url)
    products_urls = parse_products_urls(response.text, category)
    for product_url in products_urls:
        yield product_url
    next_page_url = parse_next_page(response.text, category)
    if next_page_url:
        products_page_urls = get_products_url_from_category_page(next_page_url, category)
        for product_page_url in products_page_urls:
            yield product_page_url


def _parse_description(response: str):
    soup = BeautifulSoup(response, 'lxml')
    description = soup.select_one('.description-text')
    if description:
        return description.select_one('p').text


def _parse_name(response: str):
    soup = BeautifulSoup(response, 'lxml')
    name = soup.select_one('span.name')
    if name:
        return name.text


def _parse_brand(response: str):
    soup = BeautifulSoup(response, 'lxml')
    brand = soup.select_one('span.brand')
    if brand:
        return brand.text


def save_image(url, path):
    h = httplib2.Http('.cache')
    response, content = h.request(url)
    with open(path, 'wb') as img_file:
        img_file.write(content)


def _parse_aviable(response: str):
    return sum([int(el) for el in re.findall(r'"quantity":(\d+),', response)])


def _parse_photo_url(response: str):
    soup = BeautifulSoup(response, 'lxml')
    return 'https:' + soup.select_one('img.preview-photo.j-zoom-preview')['src']


def parse_product_data(response: str):
    re_search = re.search(r'\"priceForProduct\":(\{.+?\})', response)
    if re_search:
        json_price = json.loads(re_search.group(1))
        discount = json_price.get('sale')
        price = json_price.get('priceWithSale')
        old_price = json_price.get('price')
        description = _parse_description(response)
        name = _parse_name(response)
        brand = _parse_brand(response)
        aviable = _parse_aviable(response)
        data = {'discount': discount,
                'price': price,
                'description': description,
                'name': name,
                'brand': brand,
                'aviable': aviable,
                'old_price': old_price}
        print(data)
        return data


def update_products_in_db():
    print('[INFO] Обновление продуктов в бд')
    for product in Product.select().where(Product.closed == False):
        response_product = requests.get(product.url)
        product_data = parse_product_data(response_product.text)
        if product_data['aviable'] != product.aviable:
            product.aviable = product_data['aviable']
            if product_data['aviable'] == 0:
                product.closed = True
            with open(os.path.join(config.TEMPLATES_DIRECTORY, 'template.html'), 'r',
                      encoding='utf-8') as template_file:
                template_text = template_file.read()
            template = Template(template_text)
            product_data['url'] = product.url
            text_message = template.render(product_data)
            tg_message = TelegramMessage.select().where(TelegramMessage.product == product).get()
            bot.change_post(tg_message.tg_id, text_message)
            tg_message.text = text_message
            product.save()
            tg_message.save()
            time.sleep(DELAY)


def update_new_products():
    print('[INFO] Поиск новых продуктов')
    for category in Category.select():
        print('[INFO] Категория: {}'.format(category.url))
        products_urls = get_products_url_from_category(category)
        for product_url in products_urls:
            product_in_db = Product.select().where(Product.url == product_url)
            response_product = requests.get(product_url)
            product_data = parse_product_data(response_product.text)
            if product_data['brand'] in EXCEPTION_MARKETS:
                continue
            if not product_in_db:
                with open(os.path.join(config.TEMPLATES_DIRECTORY, 'template.html'), 'r', encoding='utf-8') as template_file:
                    template_text = template_file.read()
                template = Template(template_text)
                product_data['url'] = product_url
                text_message = template.render(product_data)
                photo_url = _parse_photo_url(response_product.text)
                photo_path = os.path.join(IMG_DIRECTORY, photo_url.split('/')[-1])
                save_image(photo_url, photo_path)

                with open(photo_path, 'rb') as image:
                    message_id = bot.send_post(image, text_message)
                os.remove(photo_path)
                product_data['category'] = category
                product = Product.create(**product_data)
                TelegramMessage.create(product=product, tg_id=message_id, text=text_message)
                Photo.create(product=product, url=photo_url, path=photo_path)
                time.sleep(DELAY)


def update_products():
    update_products_in_db()
    update_new_products()


if __name__ == '__main__':
    update_products()
