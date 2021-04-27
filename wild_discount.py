import traceback
import scaner

if __name__ == '__main__':
    while True:
        try:
            scaner.update_products()
        except Exception as ex:
            print('[ERROR]')
            print(ex)
            input('Press enter...')