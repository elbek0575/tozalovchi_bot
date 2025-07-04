from telegram import Update, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackContext, filters
import os
from dotenv import load_dotenv
import re


# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL  = os.getenv("WEBHOOK_URL") + WEBHOOK_PATH
PORT = int(os.getenv("PORT", 5000))


# Глобальный счётчик обращений
request_counter = 0

# Ўзгартирилмаслиги керак бўлган user ID
ALLOWED_USER_ID = 1294217711
ALLOWED_USER_NAME = "jajglobal"

# Фильтр для проверки отправителя
def is_from_specific_bot(update: Update, bot_username: str) -> bool:
    """Проверяет, что сообщение отправлено конкретным ботом."""
    if update.message and update.message.from_user:
        return update.message.from_user.username == bot_username
    return False

# Фильтр для проверки ссылок, начинающихся с @
def contains_mention_link(update: Update) -> bool:
    """Проверяет, содержит ли сообщение ссылку, начинающуюся с @,
       и помечает её только в чатах, отличных от -1001294217711."""
    if not update.message:
        return False

    chat_id = update.message.chat.id
    # Если сообщение из “белой” группы, не помечаем его
    if chat_id == -1001294217711:
        return False

    # Проверяем текст сообщения и подпись
    text    = update.message.text    or ""
    caption = update.message.caption or ""
    if "@" in text or "@" in caption:
        return True

    # Проверяем пересланные сообщения
    if hasattr(update.message, "forward_from") and update.message.forward_from:
        forwarded_text = update.message.text or ""
        if "@" in forwarded_text:
            return True

    return False

# Фильтр для проверки рекламы или ссылок
def contains_advertisement(update: Update) -> bool:
    """Проверяет, содержит ли сообщение URL-адреса или рекламные слова."""
    if not update.message:
        return False

    chat_id = update.message.chat.id
    text    = update.message.text    or ""
    caption = update.message.caption or ""

    # Регулярное выражение для поиска URL
    url_pattern = r"(https?://|http://|www\.)\S+"
    # Ключевые слова, указывающие на рекламу
    ad_keywords = [
        "купить", "реклама", "shop", "sale", "интересно",
        "За подробностями", "прибыль", "пиши", "пишите", "ждем тебя", "ждём тебя",
        "информация", "безопасно", "ищу", "Ухοд", "на день", "день", "людей",
        "доход", "дoхoдoм", "работа", "работу", "человека", "удалёнка",
        "долларов", "oтпрaвляйтe", "в лс", "нужно", "личку", "лич",
        "легально", "КАЗИНО", "казино", "РАЗДЕВАЙ", "нехватки", "investments",
        "invest", "OPEN", "BUDGET", "OVOZ", "в месяц", "Бонус", "Бонусы",
        "КРУТИ", "ПРЯМО", "Получить", "Фальшивые", "Выиграл", "СЕКС","Секси", "SEX", "Porno", "Порно", "Оставьте заявку",
        "Оставит", "Озорная", "Озорную", "Brandbook", "Target"
        "Оставит", "Озорная", "Озорную", "Brandbook", "Target", "Казик", "Falsh", "Фальш"
    ]

    # 1) Проверка на URL в тексте — пропускаем URL только из группы -1001294217711
    if re.search(url_pattern, text):
        if chat_id != -1001294217711:
            return True

    # 2) Проверка ключевых слов в тексте
    if any(keyword.lower() in text.lower() for keyword in ad_keywords):
        return True

    # 3) Проверка на URL в подписи — тоже пропускаем URL из группы -1001294217711
    if re.search(url_pattern, caption):
        if chat_id != -1001294217711:
            return True

    # 4) Проверка ключевых слов в подписи
    if any(keyword.lower() in caption.lower() for keyword in ad_keywords):
        return True

    return False

# Фильтр для поиска скрытых и обычных телеграм-ссылок
def contains_hidden_link(update: Update) -> bool:
    """Проверяет, содержит ли сообщение скрытые или обычные Telegram-ссылки,
       при этом пропускает любые ссылки из группы -1001294217711."""
    if not update.message:
        return False

    chat_id = update.message.chat.id
    text    = update.message.text    or ""
    caption = update.message.caption or ""

    # Паттерны для скрытых ссылок
    hidden_md   = r"\[.*?\]\((https?://\S+)\)"
    hidden_html = r'<a href=["\'](https?://\S+)["\']>.*?</a>'
    # Паттерн для обычных t.me ссылок
    tg_link     = r"(?:https?://)?t\.me/\S+"

    # Если чат — наша “белая” группа, не считаем ссылки рекламой/нарушением
    if chat_id == -1001294217711:
        return False

    # В остальных чатах: если нашёл скрытую или обычную ссылку — True
    if (
        re.search(hidden_md,   text) or
        re.search(hidden_html, text) or
        re.search(hidden_md,   caption) or
        re.search(hidden_html, caption) or
        re.search(tg_link,     text) or
        re.search(tg_link,     caption)
    ):
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

# Фильтр для запрещённых слов (действует в любой группе)
def contains_prohibited_words(update: Update) -> bool:
    """Проверяет, содержит ли сообщение запрещённые слова."""
    if not update.message:
        return False

    text    = update.message.text    or ""
    caption = update.message.caption or ""
    lower_text    = text.lower()
    lower_caption = caption.lower()
    prohibited = ["секс", "порно", "sex", "porno", "real sex"]

    # Если любое из запрещённых слов есть в тексте или в подписи — помечаем True
    for word in prohibited:
        if word in lower_text or word in lower_caption:
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

        # -1 даража. Агар хабар ALLOWED_USERNAME дан бўлса, уни ўчирмаймиз
        if sender_username and sender_username.lower() == ALLOWED_USER_NAME.lower():
            print(f"[{request_counter}] Сообщение от разрешенного пользователя @{ALLOWED_USER_NAME} сохранено")
            return

        # 0. Агар хабар ALLOWED_USER_ID дан бўлса, уни ўчирмаймиз
        if sender_id == ALLOWED_USER_ID:
            print(f"[{request_counter}] Сообщение от разрешенного пользователя {ALLOWED_USER_ID} сохранено")
            return

        # 1. Проверка на администратора/владельца
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

        #  Проверяем запрещённые слова во всех группах
        if contains_prohibited_words(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Удалено из-за запрещённого имя-пользователя.")
            return

        print(f"[{request_counter}] Сообщение не удалено (не от бота, не содержит рекламу или упоминания).")
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")

def main():
    # Создаём приложение
    application = ApplicationBuilder().token(TOKEN).build()

    # Добавляем обработчик для удаления сообщений
    application.add_handler(MessageHandler(filters.ALL, delete_specific_bot_messages))

    # Heroku учун Webhook'ни ишга туширамиз
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()