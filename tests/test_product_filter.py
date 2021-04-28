import unittest
from wild_discount.scaner import ParserCategory, ProductFilter
from wild_discount.db import Category


class TestProductFilter(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open('test_category.html', encoding='utf-8') as html_file:
            response_text = html_file.read()
        cls.category = Category(url='https://test_url.com', discount=60, price_border=60000,
                                price_border_with_discount=100)
        product_blocks = ParserCategory(cls.category).get_products_blocks(response_text)
        cls.product_block = product_blocks[0]

    def test_product_filter(self):
        product_filter = ProductFilter(self.product_block, discount=self.category.discount,
                                       price_border=self.category.price_border,
                                       price_border_with_discount=self.category.price_border_with_discount).check()
        self.assertEqual(product_filter, None)


if __name__ == '__main__':
    unittest.main()
