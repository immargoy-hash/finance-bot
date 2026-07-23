import telebot
import json
import os
from datetime import datetime

# ⚠️ Замени на свой токен от BotFather
TOKEN = '8855431076:AAFCyRKDDYDtPYaejnuLlKwYp3QR9zae4qA'
bot = telebot.TeleBot(TOKEN)

DATA_FILE = 'finance_data.json'

# Загрузка данных из файла
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {'transactions': []}
    return {'transactions': []}

# Сохранение данных в файл
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Определяем, является ли тема доходом
def is_income_topic(topic_name):
    topic_clean = topic_name.lower().strip()
    return 'бабло' in topic_clean or 'доход' in topic_clean or 'плюс' in topic_clean

# Вспомогательная функция для безопасной отправки сообщений в темы
def send_safe_msg(chat_id, text, thread_id=None, parse_mode=None):
    kw = {'parse_mode': parse_mode}
    if thread_id and str(thread_id) != '0':
        kw['message_thread_id'] = int(thread_id)
    bot.send_message(chat_id, text, **kw)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    data = load_data()
    if 'transactions' not in data:
        data['transactions'] = []
    
    # Определяем ID темы и её имя
    thread_id = str(message.message_thread_id or 0)
    chat_id = message.chat.id
    
    # Определяем имя темы
    topic_name = "Основная"
    if hasattr(message, 'reply_to_message') and message.reply_to_message and message.reply_to_message.forum_topic_created:
        topic_name = message.reply_to_message.forum_topic_created.name
    elif message.message_thread_id:
        topic_name = f"Тема {message.message_thread_id}"

    text = message.text.strip() if message.text else ""
    text_lower = text.lower()

    # 1. Посмотреть сумму ТЕКУЩЕЙ темы ЗА ТЕКУЩИЙ МЕСЯЦ
    if text_lower in ['/sum', 'сумма', 'итог', 'всего']:
        current_month = datetime.now().strftime("%Y-%m")
        topic_entries = [
            e for e in data['transactions'] 
            if e.get('thread_id') == thread_id and e.get('date', '').startswith(current_month)
        ]
        total = sum(e['amount'] for e in topic_entries)
        send_safe_msg(chat_id, f"📊 В этой теме за текущий месяц: {total:.2f}", thread_id)
        return

    # 2. Полная очистка ТЕКУЩЕЙ темы
    if text_lower in ['/reset', 'сброс', 'очистить']:
        data['transactions'] = [e for e in data['transactions'] if e.get('thread_id') != thread_id]
        save_data(data)
        send_safe_msg(chat_id, "🔄 Вся история этой темы полностью удалена.", thread_id)
        return

    # 3. Текущий баланс за всё время (Доходы - Расходы)
    if text_lower in ['остаток', 'баланс', '/balance']:
        transactions = data['transactions']
        income = sum(e['amount'] for e in transactions if is_income_topic(e.get('topic_name', '')))
        expenses = sum(e['amount'] for e in transactions if not is_income_topic(e.get('topic_name', '')))
        balance = income - expenses

        msg = (
            f"💰 **Текущий баланс:**\n\n"
            f"📥 Приход: {income:.2f}\n"
            f"💸 Потрачено: {expenses:.2f}\n"
            f"➖➖➖➖➖➖➖➖➖\n"
            f"💵 Остаток на руках: {balance:.2f}"
        )
        send_safe_msg(chat_id, msg, thread_id, parse_mode="Markdown")
        return

    # 4. ИТОГ ГОДА / СТАТА
    if text_lower in ['итог года', 'статистика', 'стата', 'финансовый итог', '/year']:
        transactions = data['transactions']
        if not transactions:
            send_safe_msg(chat_id, "📊 Пока нет записанных трат!", thread_id)
            return

        total_income = 0
        expenses_by_topic = {}

        for e in transactions:
            amt = e['amount']
            t_name = e.get('topic_name', 'Основная')
            
            if is_income_topic(t_name):
                total_income += amt
            else:
                expenses_by_topic[t_name] = expenses_by_topic.get(t_name, 0) + amt
                total_expenses = sum(expenses_by_topic.values())

        report = "🎉 ГОДОВОЙ ИТОГ РАСХОДОВ И ДОХОДОВ 🎉\n\n"
        report += f"📥 Всего дали денег: {total_income:.2f}\n"
        report += f"💸 Всего просрано денег: {total_expenses:.2f}\n"
        report += "➖➖➖➖➖➖➖➖➖➖\n"
        report += "📊 **Куда улетели деньги по категориям:**\n\n"

        if expenses_by_topic:
            sorted_exp = sorted(expenses_by_topic.items(), key=lambda x: x[1], reverse=True)
            for name, amt in sorted_exp:
                percent = (amt / total_expenses * 100) if total_expenses > 0 else 0
                report += f"• {name}: {amt:.2f} ({percent:.1f}%)\n"

            top_category = sorted_exp[0]
            report += f"\n🏆 Главная статья расходов: {top_category[0]} ({top_category[1]:.2f})"
        else:
            report += "Расходов пока не было!"

        send_safe_msg(chat_id, report, thread_id, parse_mode="Markdown")
        return

    # 5. Запись входящих чисел
    try:
        val = float(text.replace(',', '.'))
        data['transactions'].append({
            'amount': val,
            'thread_id': thread_id,
            'topic_name': topic_name,
            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_data(data)
        send_safe_msg(chat_id, f"✅ Записано: {val:.2f}", thread_id)
    except ValueError:
        pass

bot.infinity_polling()
