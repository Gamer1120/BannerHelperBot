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

def get_mission_url(mission_id, mission_number):
    resp = requests.get("https://api.bannergress.com/bnrs/" + str(mission_id))
    j = resp.json()
    all_missions = j['missions']
    active_mission = all_missions[str(int(mission_number) - 1)]
    active_mission_id = active_mission['id']
    return "https://link.ingress.com/?link=https%3a%2f%2fintel.ingress.com%2fmission%2f" + active_mission_id + "&apn=com.nianticproject.ingress&isi=576505181&ibi=com.google.ingress&ifl=https%3a%2f%2fapps.apple.com%2fapp%2fingress%2fid576505181&ofl=https%3a%2f%2fintel.ingress.com%2fmission%2f" + active_mission_id + ""


async def first_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shared_url = update.message.text
    mission_details = ''
    if 'https://bannergress.com/banner/' in shared_url:
        banner_id = shared_url.replace('https://bannergress.com/banner/', '')
        resp = requests.get('https://api.bannergress.com/bnrs/' + banner_id)
        if resp.status_code is not 200:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Bannergress did not like that mission. Please report the mission to @M1chaeI so he can investigate.')
            return
        else:
            mission_details = resp.json()
            banner_id = mission_details['missions']['0']['id']
    elif 'https://link.ingress.com/?link=' in shared_url:
        banner_id = str(shared_url[-35:])
        resp = requests.get('https://api.bannergress.com/bnrs?missionId=' + banner_id)
        if resp.status_code is not 200:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text='Bannergress did not like that mission. Please report the mission to @M1chaeI so he can investigate.')
            return
        else:
            j = resp.json()
            mission_details = j[0]
    else:
        for potentiallink in update.message.entities:
            if not potentiallink['url']:
                continue
            else:
                if 'https://bannergress.com/banner/' in potentiallink:
                    banner_id = potentiallink.replace('https://bannergress.com/banner/', '')
                    resp = requests.get('https://api.bannergress.com/bnrs/' + banner_id)
                    if resp.status_code is not 200:
                        await context.bot.send_message(chat_id=update.effective_chat.id,
                                                       text='Bannergress did not like that mission. Please report the mission to @M1chaeI so he can investigate.')
                        return
                    else:
                        mission_details = resp.json()
                        banner_id = mission_details['missions']['0']['id']
                        break
        await context.bot.send_message(chat_id=update.effective_chat.id, text='That is not a correct link. Please '
                                                                              'share the mission link from the '
                                                                              'mission overview or a Bannergress link.')
        return
    reply_keyboard = [
        [InlineKeyboardButton('Open in Scanner', url=get_mission_url(mission_details['id'], "1"))],
        [InlineKeyboardButton('Next mission', callback_data=str(banner_id) + ':::1')],
    ]
    await update.message.reply_text(
        str(mission_details['title']) + "\n\n"
        "You are currently on mission: 1 of " + str(mission_details['numberOfMissions']) + "\n\n",
        reply_markup=InlineKeyboardMarkup(reply_keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )


async def next_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    split = query.data.split(':::')
    print(split)
    banner_id = split[0]
    mission_number = split[1]
    mission_number = str(int(mission_number) + 1)
    resp = requests.get('https://api.bannergress.com/bnrs?missionId=' + banner_id)
    if resp.status_code is not 200:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Bannergress did not like that mission. Please report the mission to @M1chaeI so he can investigate.')
    else:
        j = resp.json()
        print(j[0])
        mission_details = j[0]
        total_number_of_missions_in_banner = mission_details['numberOfMissions']
        if int(mission_number) > int(total_number_of_missions_in_banner):
            await query.edit_message_text(text='Looks like you completed the banner. Congrats! Don\'t forget to mark it Done on Bannergress!\n\n'
                                               'https://bannergress.com/banner/' + mission_details['id'])
        else:
            reply_keyboard = [
                [InlineKeyboardButton('Open in Scanner', url=get_mission_url(mission_details['id'], str(int(mission_number))))],
                [InlineKeyboardButton('Previous mission', callback_data=str(banner_id) + ':::' + str(int(mission_number)-2))],
                [InlineKeyboardButton('Next mission', callback_data=str(banner_id) + ':::' + mission_number)],
            ]

            await query.edit_message_text(
                    str(mission_details['title']) + "\n\n"
                                                    "You are currently on mission: "+mission_number+" of " + str(
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
