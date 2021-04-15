from peewee import *
import os

DEFAULT_DISCOUNT = 80
DB_PATH = 'data.db'
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db


class Category(BaseModel):
    url = CharField(unique=True)
    discount = IntegerField(default=DEFAULT_DISCOUNT)


class Product(BaseModel):
    url = CharField(unique=True)
    category = ForeignKeyField(Category, backref='products')
    brand = CharField()
    name = CharField()
    discount = IntegerField()
    price = FloatField()
    old_price = FloatField()
    description = TextField()
    aviable = IntegerField()
    closed = BooleanField(default=False)


class Photo(BaseModel):
    product = ForeignKeyField(Product, backref='photos')
    url = CharField(unique=True)
    path = CharField(unique=True)


class TelegramMessage(BaseModel):
    tg_id = IntegerField(unique=True)
    text = TextField()
    product = ForeignKeyField(Product, backref='telegram_messages')


def init():
    BaseModel.create_table()
    Category.create_table()
    Product.create_table()
    TelegramMessage.create_table()
    Photo.create_table()


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


if not os.path.isfile(DB_PATH):
    init()

if __name__ == '__main__':
    hand_update_categories()
