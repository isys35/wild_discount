import traceback
import scaner

if __name__ == '__main__':
    while True:
        try:
            scaner.update_products()
        except Exception as ex:
            print('[ERROR]')
            print(traceback.format_exc())
            input('Press enter...')