import requests

response = requests.get('https://www.wildberries.ru/catalog/zhenshchinam/odezhda/bluzki-i-rubashki?sort=sale&page=1')
with open('../tests/test_category.html', 'w', encoding='utf-8') as html_file:
    html_file.write(response.text)