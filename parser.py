import requests
from bs4 import BeautifulSoup

from peewee import IntegrityError

from db import Category  # ,SubCategory, SubSubCategory

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


def update_products():
    for category in Category.select():
        print(category.url)


if __name__ == '__main__':
    update_products()
