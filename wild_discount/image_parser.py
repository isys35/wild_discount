import os
import httplib2
import requests


class ImageParser:
    IMG_DIRECTORY = 'images'

    def __init__(self, url):
        self.url = url
        self.path = os.path.join(self.IMG_DIRECTORY, self.url.split('/')[-1])

    def save(self):
        if not os.path.exists(self.IMG_DIRECTORY):
            os.makedirs(self.IMG_DIRECTORY)
        response = requests.get(self.url)
        with open(self.path, 'wb') as img_file:
            img_file.write(response.content)

    def delete(self):
        os.remove(self.path)
