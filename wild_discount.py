from wild_discount import scaner, db
import traceback
import time

if __name__ == '__main__':
    while True:
        try:
            scaner.update_products()
        except Exception:
            print(traceback.format_exc())
            input("Нажмите Enter....")
            continue


