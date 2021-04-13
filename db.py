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


# class Category(BaseModel):
#     name = CharField()
#     url = CharField(unique=True)
#     data_menu_id = IntegerField(default=0)
#     discount = IntegerField(default=DEFAULT_DISCOUNT)
#
#
# class SubCategory(Category):
#     parent = ForeignKeyField(Category, backref='childrens')
#
#
# class SubSubCategory(SubCategory):
#     parent = ForeignKeyField(SubCategory, backref='childrens')


def init():
    BaseModel.create_table()
    Category.create_table()
    # SubCategory.create_table()
    # SubSubCategory.create_table()


if not os.path.isfile(DB_PATH):
    init()
