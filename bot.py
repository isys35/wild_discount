import telebot
import config
from scaner import ImageParser

bot = telebot.TeleBot(config.BOT_TOKEN)


def send_message(message):
    message = bot.send_message(chat_id=config.CHAT_NAME, text=message, parse_mode='HTML', disable_web_page_preview=True)
    return message.id


def change_message(message_id, new_message):
    message = bot.edit_message_text(chat_id=config.CHAT_NAME, message_id=message_id, text=new_message,
                                    parse_mode='HTML')
    return message.id


def send_post(img_url, message):
    image_parser = ImageParser(img_url)
    image_parser.save()
    with open(image_parser.path, 'rb') as img:
        post = bot.send_photo(chat_id=config.CHAT_NAME, photo=img, caption=message, parse_mode='HTML')
    image_parser.delete()
    return post.id


def change_post(message_id, new_message):
    post = bot.edit_message_caption(chat_id=config.CHAT_NAME, message_id=message_id, caption=new_message,
                                    parse_mode='HTML')
    return post.id


if __name__ == '__main__':
    pass
