from peewee import *
import os
import openpyxl

DEFAULT_DISCOUNT = 80
DB_PATH = 'data.db'
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


def updater_from_excel():
    wb = openpyxl.load_workbook('женщины_с_сылками.xlsx')
    ws = wb.active
    for row in ws:
        if row[0].value:
            url = row[0].value.replace('sort=popular&', '')
            print(url)
            category_in_db = DBManager().category.get_by_url(url)
            data = {'url': url, 'discount': int(row[3].value),
                    'price_border': int(row[1].value),
                    'price_border_with_discount': int(row[2].value)}
            if category_in_db:
                DBManager().category.update(data)
                continue
            DBManager().category.create(data)


if not os.path.isfile(DB_PATH):
    init()

if __name__ == '__main__':
    updater_from_excel()
