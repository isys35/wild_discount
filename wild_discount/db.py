from peewee import *
import os
from .config import BASE_DIR

DEFAULT_DISCOUNT = 80
DB_PATH = os.path.join(BASE_DIR, 'data.db')
db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    class Meta:
        database = db
        order_by = ('-id',)


class Category(BaseModel):
    url = CharField(unique=True)
    discount = IntegerField(default=DEFAULT_DISCOUNT)
    price_border = IntegerField()
    price_border_with_discount = IntegerField()


class Product(BaseModel):
    url = CharField(unique=True)
    category = ForeignKeyField(Category, backref='products')
    brand = CharField(null=True)
    name = CharField(null=True)
    discount = IntegerField(null=True)
    price = FloatField(null=True)
    old_price = FloatField(null=True)
    aviable = IntegerField(null=True)
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
        return self.model.select().order_by(self.model.id.desc())

    def create(self, data):
        return self.model.create(**data)


class DBProduct(DBMain):
    def __init__(self):
        super().__init__()
        self.model = Product

    def get_opened(self):
        return self.model.select().where(self.model.closed == False)

    def get_by_url(self, url):
        product = self.model.select().where(self.model.url == url)
        if product.exists():
            return product.get()


class DBTelegram(DBMain):
    def __init__(self):
        super().__init__()
        self.model = TelegramMessage

    def get_with_product(self, product: Product):
        message = self.model.select().where(self.model.product == product)
        if message.exists():
            return message.get()


class DBCategory(DBMain):
    def __init__(self):
        super().__init__()
        self.model = Category

    def get_by_url(self, url):
        return self.model.select().where(self.model.url == url)

    def update(self, data):
        category = self.model.get(self.model.url == data['url'])
        category.discount = data['discount']
        category.price_border = data['price_border']
        category.price_border_with_discount = data['price_border_with_discount']
        category.save()


def init():
    BaseModel.create_table()
    Category.create_table()
    Product.create_table()
    TelegramMessage.create_table()


if not os.path.isfile(DB_PATH):
    init()