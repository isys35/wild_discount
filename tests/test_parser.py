import unittest
from wild_discount.scaner import ParserProduct


class MyTestParserProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open('test_product.html', encoding='utf-8') as html_file:
            cls.response_text = html_file.read()

    def test_get_data(self):
        data = ParserProduct().get_data(self.response_text)
        should_be_data = {'discount': 40, 'price': 3540, 'name': 'Мужские классические брюки в крапинку',
                          'brand': 'MISTER A', 'aviable': 12, 'old_price': 5900}
        self.assertEqual(data, should_be_data)

    def test_get_photo_url(self):
        url = ParserProduct().get_photo_url(self.response_text)
        should_be_url = 'https://images.wbstatic.net/big/new/16680000/16687677-1.jpg'
        self.assertEqual(url, should_be_url)


class MyTestParserCategory(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open('test_category.html', encoding='utf-8') as html_file:
            cls.response_text = html_file.read()

    def test_get_photo_url(self):
        url = ParserProduct().get_photo_url(self.response_text)
        should_be_url = 'https://images.wbstatic.net/big/new/16680000/16687677-1.jpg'
        self.assertEqual(url, should_be_url)




if __name__ == '__main__':
    unittest.main()
