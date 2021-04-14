import telebot
import config

import os

bot = telebot.TeleBot(config.BOT_TOKEN)


def send_message(message):
    message = bot.send_message(chat_id=config.CHAT_NAME, text=message, parse_mode='HTML')
    return message.id


def change_message(message_id, new_message):
    message = bot.edit_message_text(chat_id=config.CHAT_NAME, message_id=message_id, text=new_message,
                                    parse_mode='HTML')
    return message.id


if __name__ == '__main__':
    pass
    # env = Environment(loader=PackageLoader(directory_name, 'templates'), autoescape=select_autoescape(['html', 'xml']))
    # template = env.get_template('template.html')
    # print(template.render({'brand':'dasdsadas', 'name':'fsafdsdfs'}))
