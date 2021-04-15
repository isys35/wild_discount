import traceback
try:
    import scaner
except Exception as ex:
    print('[ERROR]')
    print(traceback.format_exc())
    input('Press enter...')

if __name__ == '__main__':
    while True:
        try:
            scaner.update_products()
        except Exception as ex:
            print('[ERROR]')
            print(ex)
            input('Press enter...')