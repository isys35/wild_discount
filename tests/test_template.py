import unittest
from wild_discount.scaner import TemplateMessage


class TestTemplate(unittest.TestCase):
    def test_template_message(self):
        data = {'aviable': 12, 'price': 100, 'old_price': 200, 'discount': 50,
                'url': 'https://google.com', 'brand': 'Brand', 'name': 'Name'}
        message_text = TemplateMessage(data).get_text()
        print(message_text)
        self.assertEqual(sum([1, 2, 3]), 6, "Should be 6")


if __name__ == '__main__':
    unittest.main()
