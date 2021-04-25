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
    price_border = IntegerField()
    price_border_with_discount = IntegerField()


class Product(BaseModel):
    url = CharField(unique=True)
    category = ForeignKeyField(Category, backref='products')
    brand = CharField()
    name = CharField()
    discount = IntegerField()
    price = FloatField()
    old_price = FloatField()
    aviable = IntegerField()
    closed = BooleanField(default=False)


class TelegramMessage(BaseModel):
    tg_id = IntegerField(unique=True)
    text = TextField()
    product = ForeignKeyField(Product, backref='telegram_messages')


class DBManager:
    def __init__(self):
        self.product = DBProduct()
        self.telegram_message = DBTelegram()
        self.category = DBCategory()


class DBMain:
    def __init__(self):
        self.model = None

    @staticmethod
    def save(instance):
        instance.save()

    def get_all(self):
        return self.model.select()

    def create(self, data):
        return self.model.create(**data)


class DBProduct(DBMain):
    def __init__(self):
        super().__init__()
        self.model = Product

    def get_opened(self):
        return self.model.select().where(self.model.closed == False)

    def get_by_url(self, url):
        return self.model.select().where(self.model.url == url)


class DBTelegram(DBMain):
    def __init__(self):
        super().__init__()
        self.model = TelegramMessage

    def get_with_product(self, product: Product):
        return self.model.select().where(self.model.product == product).get()


class DBCategory(DBMain):
    def __init__(self):
        super().__init__()
        self.model = Category


def init():
    BaseModel.create_table()
    Category.create_table()
    Product.create_table()
    TelegramMessage.create_table()


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
    init()
