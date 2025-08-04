import telebot

TOKEN = '7699157540:AAFKnOksbFwShTJLnLs5YGoyck2ZeNBWot8'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, '''
💡 INFORMAT Kursuna xoş gəlmisiniz!

Qiymət: 199 AZN

📌 Ödəniş üçün üsul seçin:

🔸 Kart (M10): +994502124244
🔸 Kripto (USDT TRC20): TQGQaWprxB8YRsDtwJNc8XA1mmBopZ3QFG
🔸 Kripto (TON): UQBayfO8cTYaF0bC3aBxzx3QSSj1--_piQ_w13h7ELisevB5

📩 Ödəniş etdikdən sonra screenshot göndərin.
''')

@bot.message_handler(content_types=['photo', 'text'])
def handle_payment(message):
    bot.send_message(message.chat.id, '✅ Ödənişiniz yoxlanılır.')
    bot.send_message(459247125, f'📩 Yeni ödəniş: @{message.from_user.username or message.chat.id}')

@bot.message_handler(commands=['sendpdf'])
def send_pdf(message):
    if message.chat.id == 459247125:
        try:
            with open('informat_ticaret_kursu.pdf', 'rb') as pdf:
                bot.send_document(message.reply_to_message.forward_from.id, pdf)
                bot.send_message(459247125, '✅ PDF göndərildi.')
        except Exception as e:
            bot.send_message(459247125, f'Xəta: {e}')

bot.polling()