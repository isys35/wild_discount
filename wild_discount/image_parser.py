import os
import httplib2


class ImageParser:
    IMG_DIRECTORY = 'images'

    def __init__(self, url):
        self.url = url
        self.path = os.path.join(self.IMG_DIRECTORY, self.url.split('/')[-1])

    def save(self):
        if not os.path.exists(self.IMG_DIRECTORY):
            os.makedirs(self.IMG_DIRECTORY)
        h = httplib2.Http('.cache')
        response, content = h.request(self.url)
        with open(self.path, 'wb') as img_file:
            img_file.write(content)

    def delete(self):
        os.remove(self.path)
