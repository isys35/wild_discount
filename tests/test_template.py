import unittest
from wild_discount.scaner import TemplateMessage


class TestTemplate(unittest.TestCase):
    def test_template_message(self):
        data = {'aviable': 12, 'price': 100, 'old_price': 200, 'discount': 50,
                'url': 'https://google.com', 'brand': 'Brand', 'name': 'Name'}
        should_be_text = '\n<b>В наличиии:</b> 12\n<b>Цена:</b> 100 руб <s>200 руб.</s>\n<b>Скидка</b> -50%\n\n' \
                         '<a href="https://google.com">Brand / Name</a>'
        message_text = TemplateMessage(data).get_text()
        self.assertEqual(message_text, should_be_text)


if __name__ == '__main__':
    unittest.main()
