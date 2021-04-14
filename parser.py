import requests
from bs4 import BeautifulSoup
import re
import json
import time

from peewee import IntegrityError

from db import Category, Product, TelegramMessage
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


def save_page(response: str, file_name='page.html'):
    with open(file_name, 'w', encoding='utf8') as html_file:
        html_file.write(response)


def hand_update_categories():
    while True:
        url = input('Введите ссылку на категорию: ')
        discount = input('Введите скидку(80 по умолчанию):')
        if not discount:
            try:
                Category.create(url=url)
                print('[INFO] Категория сохранена')
            except IntegrityError:
                continue
        else:
            try:
                Category.create(url=url, discount=int(discount))
                print('[INFO] Категория сохранена')
            except IntegrityError:
                continue


def parse_products_urls(response: str, category: Category):
    soup = BeautifulSoup(response, 'lxml')
    products_blocks = soup.select('.dtList.i-dtList.j-card-item.no-left-part')
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


def _parse_aviable(response: str):
    return sum([int(el) for el in re.findall(r'"quantity":(\d+),', response)])


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
        return {'discount': discount,
                'price': price,
                'description': description,
                'name': name,
                'brand': brand,
                'aviable': aviable,
                'old_price': old_price}
    else:
        save_page(response)


def update_products():
    for category in Category.select():
        products_urls = get_products_url_from_category(category)
        for product_url in products_urls:
            product_in_db = Product.select().where(Product.url == product_url)
            response_product = requests.get(product_url)
            product_data = parse_product_data(response_product.text)
            product_data['url'] = product_url
            product_data['category'] = category
            if not product_in_db:
                template = config.JINJA_ENV.get_template('template.html')
                text_message = template.render(product_data)
                message_id = bot.send_message(text_message)
                product = Product.create(**product_data)
                TelegramMessage.create(product=product, tg_id=message_id, text=text_message)
                time.sleep(1)


def test():
    with open('page.html', 'r', encoding='utf-8') as html_file:
        response_product = html_file.read()
    product_data = parse_product_data(response_product)
    template = config.JINJA_ENV.get_template('template.html')
    context = {'brand': product_data.get('brand'),
               'name': product_data.get('name'),
               'description': product_data.get('description'),
               'aviable': product_data.get('aviable')}
    message = bot.send_message('123123')
    print(message)
    time.sleep(3)
    bot.change_message(message, 'Ууупс')


if __name__ == '__main__':
    # update_products()
    # while True:
    #     try:
    #         test()
    #         break
    #     except Exception as ex:
    #         print(ex)
    #         continue
    response = requests.get('https://by.wildberries.ru/catalog/14565809/detail.aspx')
    save_page(response.text, 'page2.html')
