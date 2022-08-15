import requests
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import filters, MessageHandler, CommandHandler, ContextTypes, ApplicationBuilder, CallbackQueryHandler

import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TELEGRAM_ACCESS_TOKEN = ''


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Yo just share a banner link')


def get_mission_url(bannergress_mission_id, mission_number):
    resp = requests.get("https://api.bannergress.com/bnrs/" + str(bannergress_mission_id))
    j = resp.json()
    all_missions = j['missions']
    active_mission = all_missions[str(int(mission_number) - 1)]
    active_mission_id = active_mission['id']
    return "https://link.ingress.com/?link=https%3a%2f%2fintel.ingress.com%2fmission%2f" + active_mission_id + "&apn=com.nianticproject.ingress&isi=576505181&ibi=com.google.ingress&ifl=https%3a%2f%2fapps.apple.com%2fapp%2fingress%2fid576505181&ofl=https%3a%2f%2fintel.ingress.com%2fmission%2f" + active_mission_id + ""


# Gets an Update and returns a title, total number of missions as string and the Niantic ID of the first mission
def parse_first_message(update: Update):
    message = update.message.text

    # The message is a Bannergress URL
    if 'https://bannergress.com/banner/' in message:
        bannergress_banner_id = message.replace('https://bannergress.com/banner/', '')
        bannergress_banner = requests.get('https://api.bannergress.com/bnrs/' + bannergress_banner_id)
        if bannergress_banner.status_code is not 200:
            raise Exception('It looks like you are not sharing a correct Bannergress URL. Please double-check your '
                            'URL or contact @M1chaeI if you think this is a bug, so it can be investigated.')
        else:
            bannergress_banner_json = bannergress_banner.json()
            return bannergress_banner_json['title'], bannergress_banner_json['id'], bannergress_banner_json['numberOfMissions'], \
                   bannergress_banner_json['missions']['0']['id']
    # The message is a link shared from the Ingress scanner
    elif 'https://link.ingress.com/?link=' in message:
        niantic_first_mission_id = str(message[-35:])
        resp = requests.get('https://api.bannergress.com/bnrs?missionId=' + niantic_first_mission_id)
        if resp.status_code is not 200:
            raise Exception(
                'It looks like you are not sharing a correct URL from within Ingress. Please double-check your URL or '
                'contact @M1chaeI if you think this is a bug, so it can be investigated.')
        else:
            bannergress_mission = resp.json()[0]
            return bannergress_mission['title'], bannergress_mission['id'], bannergress_mission['numberOfMissions'], niantic_first_mission_id
    # The message might contain a link to a banner somewhere in the message
    else:
        for entity in update.message.entities:
            if not entity or not entity['url']:
                continue
            else:
                url = str(entity['url'])
                if 'https://bannergress.com/banner/' in url:
                    bannergress_banner_id = url.replace('https://bannergress.com/banner/', '')
                    bannergress_banner = requests.get('https://api.bannergress.com/bnrs/' + bannergress_banner_id)
                    if bannergress_banner.status_code is not 200:
                        raise Exception(
                            'It looks like there was some kind of invalid Bannergress link in your message. Please '
                            'double-check your URL or contact @M1chaeI if you think this is a bug, so it can be '
                            'investigated.')
                    else:
                        bannergress_banner = bannergress_banner.json()
                        niantic_first_mission_id = bannergress_banner['missions']['0']['id']
                        return bannergress_banner['title'], bannergress_banner['id'], bannergress_banner['numberOfMissions'], niantic_first_mission_id

    raise Exception('It looks like your message did not contain a Bannergress link or a mission link sent from the'
                    'Ingress scanner. Please double-check your URL or contact @M1chaeI if you think this is a bug, so'
                    'it can be investigated.')


async def first_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = ''
    bannergress_id = ''
    total_number_of_missions = 0
    niantic_first_mission_id = ''

    try:
        title, bannergress_id, total_number_of_missions, niantic_first_mission_id = parse_first_message(update)
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=str(e))
        return

    reply_keyboard = [
        [InlineKeyboardButton('Open in Scanner', url=get_mission_url(bannergress_id, "1"))],
        [InlineKeyboardButton('Next mission', callback_data=niantic_first_mission_id + ':::1')],
    ]
    await update.message.reply_text(
        title + "\n\nYou are currently on mission: 1 of " + str(total_number_of_missions) + "\n\n",
        reply_markup=InlineKeyboardMarkup(reply_keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def next_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    split = query.data.split(':::')
    banner_id = split[0]
    mission_number = split[1]
    mission_number = str(int(mission_number) + 1)
    resp = requests.get('https://api.bannergress.com/bnrs?missionId=' + banner_id)
    if resp.status_code is not 200:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Bannergress did not like that mission. Please report the mission to @M1chaeI so he can investigate.')
    else:
        j = resp.json()
        mission_details = j[0]
        total_number_of_missions = mission_details['numberOfMissions']
        if int(mission_number) > int(total_number_of_missions):
            await query.edit_message_text(
                text='Looks like you completed the banner. Congrats! Don\'t forget to mark it Done on Bannergress!\n\n'
                     'https://bannergress.com/banner/' + mission_details['id'])
        else:
            reply_keyboard = [
                [InlineKeyboardButton('Open in Scanner',
                                      url=get_mission_url(mission_details['id'], str(int(mission_number))))],
                [InlineKeyboardButton('Previous mission',
                                      callback_data=str(banner_id) + ':::' + str(int(mission_number) - 2))],
                [InlineKeyboardButton('Next mission', callback_data=str(banner_id) + ':::' + mission_number)],
            ]

            await query.edit_message_text(
                str(mission_details['title']) + "\n\n"
                                                "You are currently on mission: " + mission_number + " of " + str(
                    mission_details['numberOfMissions']) + "\n\n",
                reply_markup=InlineKeyboardMarkup(reply_keyboard),
                parse_mode=ParseMode.MARKDOWN_V2
            )


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_ACCESS_TOKEN).build()
    start_handler = CommandHandler('start', start)
    first_mission_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), first_mission)

    application.add_handler(start_handler)
    application.add_handler(first_mission_handler)
    application.add_handler(CallbackQueryHandler(next_mission))

    application.run_polling()
