from telegram import Update, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackContext, filters
import os
from dotenv import load_dotenv
import re

# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("BOT")

# Глобальный счётчик обращений
request_counter = 0

# Фильтр для проверки отправителя
def is_from_specific_bot(update: Update, bot_username: str) -> bool:
    """Проверяет, что сообщение отправлено конкретным ботом."""
    if update.message and update.message.from_user:
        return update.message.from_user.username == bot_username
    return False

# Фильтр для проверки ссылок, начинающихся с @
def contains_mention_link(update: Update) -> bool:
    """Проверяет, содержит ли сообщение ссылку, начинающуюся с @."""
    if update.message:
        # Проверяем текст сообщения
        text = update.message.text or ""
        if "@" in text:
            return True

        # Проверяем подпись медиа
        caption = update.message.caption or ""
        if "@" in caption:
            return True

        # Проверяем пересланные сообщения (только если атрибут доступен)
        if hasattr(update.message, "forward_from") and update.message.forward_from:
            forwarded_text = update.message.text or ""
            if "@" in forwarded_text:
                return True

    return False

# Фильтр для проверки рекламы или ссылок
def contains_advertisement(update: Update) -> bool:
    """Проверяет, содержит ли сообщение URL-адреса или рекламные слова."""
    if update.message:
        # Проверяем текст сообщения
        text = update.message.text or ""
        # Проверяем подпись, если есть медиа
        caption = update.message.caption or ""
        # Регулярное выражение для поиска URL
        url_pattern = r"(https?://|http://|www\.)\S+"
        # Ключевые слова, указывающие на рекламу
        ad_keywords = ["купить", "реклама", "shop", "sale", "http", "https", "интересно", "За подробностями", "прибыль", "пиши", "пишите", "ждем тебя", "ждём тебя", "информация", "безопасно",
                       "ищу", "Ухοд", "на день", "день", "людей", "доход", "дoхoдoм", "работа", "работу", "человека", "удалёнка", "доллар", "долларов", "oтпрaвляйтe", "в лс", "нужно", "личку", "лич", "легально",
                       "КАЗИНО", "казино", "РАЗДЕВАЙ", "нехватки", "investments", "invest", "OPEN", "BUDGET", "OVOZ", "в месяц"]
        # Проверяем на наличие URL или ключевых слов
        if re.search(url_pattern, text) or any(keyword.lower() in text.lower() for keyword in ad_keywords):
            return True

        if re.search(url_pattern, caption) or any(keyword.lower() in caption.lower() for keyword in ad_keywords):
            return True
    return False

# Фильтр для поиска скрытых ссылок (Markdown и HTML)
def contains_hidden_link(update: Update) -> bool:
    """Проверяет, содержит ли сообщение скрытые ссылки."""
    if update.message:
        text = update.message.text or ""
        caption = update.message.caption or ""

        # Регулярное выражение для поиска скрытых ссылок
        hidden_link_pattern = r"\[.*?\]\((https?://\S+)\)"  # Markdown формат
        hidden_link_pattern_html = r'<a href=["\'](https?://\S+)["\']>.*?</a>'  # HTML формат
        telegram_link_pattern = r"(?:https?://)?t\.me/\S+"  # Телеграм-ссылки

        # Проверяем текст и подпись к медиа
        if (re.search(hidden_link_pattern, text) or
                re.search(hidden_link_pattern_html, text) or
                re.search(telegram_link_pattern, text)):
            return True
        if (re.search(hidden_link_pattern, caption) or
                re.search(hidden_link_pattern_html, caption) or
                re.search(telegram_link_pattern, caption)):
            return True

    return False

# Проверка, является ли отправитель администратором или владельцем
async def is_admin_or_owner(chat_id: int, user_id: int, context: CallbackContext) -> bool:
    """Проверяет, является ли пользователь администратором или владельцем группы."""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.id == user_id and isinstance(admin, (ChatMemberAdministrator, ChatMemberOwner)):
                return True
    except Exception as e:
        print(f"Ошибка при проверке администратора: {e}")
    return False

# Проверка, является ли сообщение системным или содержит текст '. теперь в группе'
def contains_group_join_message(update: Update) -> bool:
    """Проверяет, является ли сообщение системным о добавлении участника или содержит текст '. теперь в группе'."""
    if update.message:
        # Проверка на системное сообщение о добавлении участника
        if bool(update.message.new_chat_members):
            return True

        # Проверка текста на точное совпадение с '. теперь в группе'
        text = update.message.text or ""
        if text.strip() == " теперь в группе":
            return True

    return False

# Обработчик для удаления сообщений
async def delete_specific_bot_messages(update: Update, context: CallbackContext) -> None:
    global request_counter
    request_counter += 1

    try:
        # Получаем информацию о чате и сообщении
        chat_title = update.message.chat.title if update.message.chat.title else "Личный чат"
        chat_id = update.message.chat_id
        sender_username = update.message.from_user.username if update.message.from_user else "Неизвестно"
        sender_id = update.message.from_user.id if update.message.from_user else "Неизвестно"
        sender_is_bot = update.message.from_user.is_bot if update.message.from_user else False

        # Логируем все данные
        print(f"[{request_counter}] Отправитель: @{sender_username}, ID: {sender_id}, Группа: '{chat_title}' (ID: {chat_id})")
        print(f"[{request_counter}] Текст сообщения: {update.message.text or 'Нет текста'}")
        print(f"[{request_counter}] Тип чата: {update.message.chat.type}")

        # Если отправитель администратор или владелец, не удаляем сообщение
        if await is_admin_or_owner(chat_id, sender_id, context):
            print(f"[{request_counter}] Сообщение не удалено, так как отправитель администратор или владелец группы.")
            return

        # Удаляем сообщения от любого бота
        if sender_is_bot:
            message_id = update.message.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"[{request_counter}] Сообщение от бота @{sender_username} удалено в группе '{chat_title}'.")
            return

        # Удаляем сообщения, содержащие упоминания (@логин)
        if contains_mention_link(update):
            message_id = update.message.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"[{request_counter}] Сообщение с упоминанием @{sender_username} удалено в группе '{chat_title}'.")
            return

        # Удаляем сообщения с рекламой или URL
        if contains_advertisement(update):
            message_id = update.message.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"[{request_counter}] Рекламное сообщение удалено в группе '{chat_title}'.")
            return

        # Удаляем сообщения с текстом '. теперь в группе' или системные о добавлении участников
        if contains_group_join_message(update):
            message_id = update.message.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"[{request_counter}] Сообщение с текстом '. теперь в группе' или системное сообщение о добавлении удалено в группе '{chat_title}'.")
            return

        # Удаляем сообщения с рекламой, упоминаниями, ботами или скрытыми ссылками
        if contains_advertisement(update) or contains_mention_link(update) or contains_hidden_link(update):
            message_id = update.message.message_id
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            print(f"Рекламное или скрытое ссылочное сообщение от @{sender_username} удалено.")
            return

        print(f"[{request_counter}] Сообщение не удалено (не от бота, не содержит рекламу или упоминания).")
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

def main():
    # Создаём приложение
    application = ApplicationBuilder().token(TOKEN).build()

    # Добавляем обработчик для удаления сообщений
    application.add_handler(MessageHandler(filters.ALL, delete_specific_bot_messages))

    # Запускаем приложение
    application.run_polling()

if __name__ == "__main__":
    main()
