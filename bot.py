import os, re
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackContext, filters, CommandHandler
from dotenv import load_dotenv
from telegram.constants import ChatType
from pathlib import Path
import json
from urllib.parse import urlparse, urljoin
from telegram._chatmember import ChatMemberAdministrator, ChatMemberOwner
from telegram.constants import ChatType
from telegram.error import TelegramError, Forbidden, BadRequest
import html

# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook").strip()
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "").strip()
PORT = int(os.getenv("PORT", 5000))


# Глобальный счётчик обращений
request_counter = 0

# Ўзгартирилмаслиги керак бўлган user ID
ALLOWED_USER_ID = 1294217711
ALLOWED_USER_NAME = "jajglobal"

# IDлар ва username’лар рўйхати .env орқали ҳам берилса бўлади:
ALLOWED_USER_IDS = {
    int(x) for x in os.getenv("ALLOWED_USER_IDS", "747789912").split(",")
    if x.strip().isdigit()
}
ALLOWED_USERNAMES = {
    u.strip().lower() for u in os.getenv("ALLOWED_USERNAMES", "").split(",")
    if u.strip()
}


def build_full_webhook_url(base: str, path: str) -> str | None:
    if not base:
        return None
    base = base.rstrip("/") + "/"
    path = path.lstrip("/")
    return urljoin(base, path)

def is_valid_public_https(url: str) -> bool:
    try:
        u = urlparse(url)
        if u.scheme != "https" or not u.netloc:
            return False
        bad_hosts = ("127.", "10.", "192.168.", "localhost")
        return not any((u.hostname or "").startswith(b) for b in bad_hosts)
    except Exception:
        return False

FULL_WEBHOOK_URL = build_full_webhook_url(WEBHOOK_BASE, WEBHOOK_PATH)
print(f"Webhook URL candidate: {FULL_WEBHOOK_URL!r}")

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

# --- Динамик реклама сўзлари конфиги ---
KEYWORDS_FILE = Path(os.getenv("AD_KEYWORDS_FILE", "ad_keywords.json"))

# Фойдаланувчи қўшган (динамик) сўзлар
AD_CUSTOM_KEYWORDS: set[str] = set()

def load_custom_keywords() -> None:
    try:
        if KEYWORDS_FILE.exists():
            data = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                AD_CUSTOM_KEYWORDS.update([str(x).lower() for x in data])
    except Exception as e:
        print(f"⚠️ Ключ сўзларни юклашда хатолик: {e}")

def save_custom_keywords() -> None:
    try:
        KEYWORDS_FILE.write_text(
            json.dumps(sorted(list(AD_CUSTOM_KEYWORDS)), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"⚠️ Ключ сўзларни сақлашда хатолик: {e}")


# Ҳаммасини бирлаштирадиган хелпер
def all_keywords_lower() -> set[str]:
    # Фақат custom (ad_keywords.json)га таянамиз
    return {str(k).lower() for k in AD_CUSTOM_KEYWORDS}


# Модул юкланишида кастом сўзларни очиб оламиз
load_custom_keywords()


def contains_advertisement(update: Update) -> bool:
    """Проверяет, содержит ли сообщение URL-адреса или рекламные слова."""
    if not update.message:
        return False

    chat_id = update.message.chat.id
    text    = update.message.text    or ""
    caption = update.message.caption or ""

    url_pattern = r"(https?://|http://|www\.)\S+"

    # 1) URL текшируви (оқ рўйхатдаги гуруҳдан ташқарида)
    if re.search(url_pattern, text):
        if chat_id != -1001294217711:
            return True

    # 2) Ключ сўз/ибораларга текшириш (текстда)
    lower_text = text.lower()
    if any(k in lower_text for k in all_keywords_lower()):
        return True

    # 3) URL текшируви – сарлавҳада
    if re.search(url_pattern, caption):
        if chat_id != -1001294217711:
            return True

    # 4) Ключ сўз/ибораларга текшириш (сарлавҳада)
    lower_caption = caption.lower()
    if any(k in lower_caption for k in all_keywords_lower()):
        return True

    return False

async def add_keyword(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return

    chat_id = update.message.chat_id
    user    = update.message.from_user
    user_id = user.id if user else None
    username = ((user.username or "").lower()) if user else ""

    # 🔓 Рухсат: ID ёки username орқали
    is_allowed = (user_id in ALLOWED_USER_IDS) or (username in ALLOWED_USERNAMES)

    if not is_allowed and user_id is not None:
        # Гуруҳда админми ёки private’да эгами — шуни ҳам текшириб оламиз
        is_allowed = await is_admin_or_owner(chat_id, user_id, context)

    if not is_allowed:
        await update.message.reply_text("❌ Бу буйруқни фақат админ ёки рухсат этилган фойдаланувчи бажаради.")
        return

    # '/add' ёки '/ add' — иккаласини ҳам қўллаймиз
    raw = update.message.text or ""
    m = re.match(r"^/\s*add\b\s*(.*)$", raw, flags=re.IGNORECASE | re.DOTALL)
    phrase = (m.group(1) if m else "").strip()

    if not phrase:
        await update.message.reply_text("Ишлатиш: /add <фраза>\nМисол: /add Керакли фразани қўшинг")
        return

    lower = phrase.lower()
    # Илгариги: if lower in all_keywords_lower():
    # Янгиси: фақат custom’да бор-йўқни текшириш
    if lower in AD_CUSTOM_KEYWORDS:
        await update.message.reply_text("⚠️ Бу ибора аллақачон фильтрда бор.")
        return

    AD_CUSTOM_KEYWORDS.add(lower)
    try:
        save_custom_keywords()
    except Exception:
        pass

    await _reply_privately_or_here(
        update,
        context,
        f"✅ Сиз юборган фраза(лар) фильтрга қўшилди: <code>{html.escape(phrase)}</code>",
        parse_mode="HTML",
    )

def _format_list(items: list[str] | set[str]) -> str:
    items = [x for x in (items or []) if str(x).strip()]
    if not items:
        return "— (бўш)"
    unique_sorted = sorted(set(items), key=lambda s: s.lower())
    return "\n".join(f"• {x}" for x in unique_sorted)


def _split_chunks(s: str, n: int = 3900):
    for i in range(0, len(s), n):
        yield s[i:i+n]

async def show_keywords(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return

    chat_id = update.message.chat_id
    user    = update.message.from_user
    user_id = user.id if user else None
    username = (user.username or "").lower() if user and user.username else ""

    # # Рухсат
    # is_allowed = (user_id in ALLOWED_USER_IDS) or (username in ALLOWED_USERNAMES)
    # if not is_allowed and user_id is not None:
    #     is_allowed = await is_admin_or_owner(chat_id, user_id, context)
    # if not is_allowed:
    #     await update.message.reply_text("❌ Бу буйруқни фақат админ ёки рухсат этилган фойдаланувчи кўра олади.")
    #     return

    # Файлдан custom рўйхатни ўқиб оламиз
    custom = []
    try:
        if KEYWORDS_FILE.exists():
            data = json.loads(KEYWORDS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                custom = [str(x).strip() for x in data if str(x).strip()]
        else:
            custom = sorted(list(AD_CUSTOM_KEYWORDS))
    except Exception:
        custom = sorted(list(AD_CUSTOM_KEYWORDS))

    txt = "🗂️ ad_keywords.json (custom):\n" + _format_list(custom)

    for chunk in _split_chunks(txt):
        await update.message.reply_text(chunk, disable_web_page_preview=True)

    # ✅ Қўшимча изоҳ
    await update.message.reply_text(
        "ℹ️ Ҳозирча фильтрнинг тўлиқ таркиби шу фразалардан иборат.",
        disable_web_page_preview=True
    )


async def ins_help(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return

    # 🔐 /ins — фақат админ/рухсат этилган фойдаланувчи
    chat_id = update.message.chat_id
    user    = update.message.from_user
    user_id = user.id if user else None
    username = (user.username or "").lower() if user and user.username else ""

    is_allowed = (user_id in ALLOWED_USER_IDS) or (username in ALLOWED_USERNAMES)
    if not is_allowed and user_id is not None:
        is_allowed = await is_admin_or_owner(chat_id, user_id, context)
    if not is_allowed:
        await update.message.reply_text("❌ Бу буйруқни фақат гурух админлари ёки рухсат этилган фойдаланувчи қўллай олади.")
        return

    help_html = (
        "<b>📘 Фильтр-бот бўйича қисқача йўриқнома</b>\n\n"
        "• <b>/add &lt;фраза&gt;</b> — фильтрга янги ибора қўшиш.\n"
        "  Мисол: <code>/add Керакли фраза ёки жумлани қўшиб ёзинг</code>\n\n"
        "• <b>/del &lt;фраза&gt;</b> — фильтрдан кўрсатилган иборани ўчириш.\н"
        "  Мисол: <code>/del Керакли фраза ёки жумлани қўшиб ёзинг</code>\n\n"
        "• <b>/show</b> — ҳозирги фильтр рўйхатини кўриш.\n"
        "  Мисол: <code>/show</code>\n\n"
        "• <b>/ins</b> — шу йўриқномани қайта чиқаради.\n\n\n"
        "<i>Эслатмалар:</i>\n\n"
        "— Фразалар <code>ad_keywords.json</code> га сақланади; қўшилгандан кейин дарҳол кучга киради.\n\n"
        "— Гуруҳда фақат <b>админ/рухсат этилган фойдаланувчи</b> /add ва /del ни ишлатади.\n\n"
        "— Private чатда автоматик ўчириш йўқ, у фақат гуруҳларни “тозалаш” учун йўлга қўйилган."
    )

    for chunk in _split_chunks(help_html, 3800):
        await update.message.reply_text(help_html, parse_mode="HTML", disable_web_page_preview=True)
    # for chunk in _split_chunks(txt):
    #     await _reply_privately_or_here(
    #         update, context,
    #         f"<pre>{html.escape(chunk)}</pre>",
    #         parse_mode="HTML",
    #     )


async def del_keyword(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return

    chat_id = update.message.chat_id
    user    = update.message.from_user
    user_id = user.id if user else None
    username = (user.username or "").lower() if user and user.username else ""

    # 🔓 Рухсат: ID/username ёки админ/эгаси
    is_allowed = (user_id in ALLOWED_USER_IDS) or (username in ALLOWED_USERNAMES)
    if not is_allowed and user_id is not None:
        is_allowed = await is_admin_or_owner(chat_id, user_id, context)
    if not is_allowed:
        await update.message.reply_text("❌ Бу буйруқни фақат админ ёки рухсат этилган фойдаланувчи бажаради.")
        return

    # '/del' ёки '/ del' — иккаласини ҳам қўллаймиз
    raw = update.message.text or ""
    m = re.match(r"^/\s*del\b\s*(.*)$", raw, flags=re.IGNORECASE | re.DOTALL)
    phrase = (m.group(1) if m else "").strip()
    if not phrase:
        await update.message.reply_text("Ишлатиш: /del <фраза>\nМисол: /del Керакли фразани қўшинг")
        return

    lower = phrase.lower()

    # ❗ faqat CUSTOM тўпламдан ўчирилади (default’га тегмаймиз)
    if lower in AD_CUSTOM_KEYWORDS:
        AD_CUSTOM_KEYWORDS.remove(lower)
        try:
            save_custom_keywords()
        except Exception:
            pass
        await _reply_privately_or_here(
            update, context,
            f"🗑️ Ўчирилган фразалар: <code>{html.escape(phrase)}</code>",
            parse_mode="HTML",
        )
    else:
        # Ихтиёрий: яқин мослар (substring) топиш — фойдаланувчига ёрдам учун
        similar = [k for k in sorted(AD_CUSTOM_KEYWORDS) if lower in k]
        if similar:
            preview = "\n".join(f"• {s}" for s in similar[:20])
            await update.message.reply_text(
                "Тўлиқ мос фразалар топилмади. Қуйида ўхшаш (substring) элементлар бор:\n" + preview
            )
        else:
            await update.message.reply_text("⚠️ Бу фраза custom фильтрларда топилмади.")



async def seed_defaults(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return

    chat_id = update.message.chat_id
    user    = update.message.from_user
    user_id = user.id if user else None
    username = (user.username or "").lower() if user and user.username else ""

    # 🔓 Рухсат: ID/username ёки админ/эгаси
    is_allowed = (user_id in ALLOWED_USER_IDS) or (username in ALLOWED_USERNAMES)
    if not is_allowed and user_id is not None:
        is_allowed = await is_admin_or_owner(chat_id, user_id, context)
    if not is_allowed:
        await update.message.reply_text("❌ Бу буйруқни фақат админ ёки рухсат этилган фойдаланувчи бажаради.")
        return

async def _reply_privately_or_here(update: Update, context: CallbackContext, text: str, *, parse_mode: str = "HTML"):
    if not update.message:
        return
    msg = update.message
    chat = msg.chat
    user = msg.from_user
    user_id = user.id if user else None

    # Гуруҳ/супергруппа → аввало DM'га уринамиз
    if chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) and user_id:
        try:
            await context.bot.send_message(
                chat_id=user_id, text=text, parse_mode=parse_mode, disable_web_page_preview=True
            )
            # Ихтиёрий: гуруҳда қисқа тасдиқ хабар қолдирамиз
            await msg.reply_text("📬 Жавоб шахсий чатингизга юборилди.", quote=True)
            return
        except Forbidden:
            # Фойдаланувчи бот билан private'да /start қилмаган
            bot_username = (context.bot.username or "").lstrip("@")
            deep = f"https://t.me/{bot_username}?start=hi" if bot_username else ""
            note = "⚠️ Бот сизга шахсийга ёза олмайди. Илтимос, бот билан private’да /start юборинг."
            if deep:
                note += f"\n👉 {deep}"
            await msg.reply_text(note)
            return
        except BadRequest:
            # бошқа хато бўлса — гуруҳнинг ўзига жавоб қайтарамиз
            pass

    # Private чат ёки DM юбориш амалга ошмаган — шу чатнинг ўзида
    await msg.reply_text(text, parse_mode=parse_mode, disable_web_page_preview=True)


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
    # 0) Ҳамиша-рухсат этилган ID → дарров True
    if user_id in ALLOWED_USER_IDS:
        return True

    # 1) Private чат: админлар рўйхати йўқ. Чат эгаси = ўзи.
    #    Privateда одатда chat_id == user_id бўлади.
    if chat_id > 0:  # манфий bo'lsa supergroup/channel
        return user_id == chat_id

    # 2) Гуруҳ/супергруппада одатий админ текшируви
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        for admin in admins:
            if admin.user.id == user_id and isinstance(admin, (ChatMemberAdministrator, ChatMemberOwner)):
                return True
    except Exception as e:
        print(f"Админ текширувида хатолик: {e}")
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
    if not update.message:
        return

    msg_text = update.message.text or ""
    chat = update.message.chat

    # Командаларни ҳеч қачон ўчирмаймиз
    if re.match(r"^/\s*(add|del|show|ins)\b", msg_text, flags=re.IGNORECASE):
        return

    chat = update.message.chat
    msg_text = update.message.text or ""

    # 🔕 Private чатда умуман ўчирмаймиз (гуруҳ тозалаш учун керак)
    if chat.type == ChatType.PRIVATE:
        return

    # 🔒 /add ёки / add буйруқлари ҳеч қачон ўчирилмайди
    if re.match(r"^/\s*add\b", msg_text, flags=re.IGNORECASE):
        return

    global request_counter
    request_counter += 1

    # 🔒 Қайта-ихтиёт guard
    if msg_text.startswith("/add"):
        print(f"[{request_counter}] /add буйруғи қабул қилинди, ўчирилмайди.")
        return

    try:
        chat_title = update.message.chat.title if update.message.chat.title else "Личный чат"
        chat_id = update.message.chat_id
        sender_username = update.message.from_user.username if update.message.from_user else "Неизвестно"
        sender_id = update.message.from_user.id if update.message.from_user else "Неизвестно"
        sender_is_bot = update.message.from_user.is_bot if update.message.from_user else False

        print(f"[{request_counter}] Отправитель: @{sender_username}, ID: {sender_id}, Группа: '{chat_title}' (ID: {chat_id})")
        print(f"[{request_counter}] Текст сообщения: {update.message.text or 'Нет текста'}")
        print(f"[{request_counter}] Тип чата: {update.message.chat.type}")

        # -1. Рухсат этилган username
        if sender_username and sender_username.lower() == ALLOWED_USER_NAME.lower():
            print(f"[{request_counter}] Сообщение от разрешенного пользователя @{ALLOWED_USER_NAME} сохранено")
            return

        # 0. Рухсат этилган ID
        if sender_id in ALLOWED_USER_IDS:
            print(f"[{request_counter}] Сообщение от разрешенного пользователя {sender_id} сохранено")
            return

        # 1. Админ/эга — ўчирмаймиз
        if await is_admin_or_owner(chat_id, sender_id, context):
            print(f"[{request_counter}] Сообщение не удалено, так как отправитель администратор или владелец группы.")
            return

        # 2. Ботдан келса — ўчириш
        if sender_is_bot:
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Сообщение от бота @{sender_username} удалено в группе '{chat_title}'.")
            return

        # 3. @mention — ўчириш
        if contains_mention_link(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Сообщение с упоминанием @{sender_username} удалено в группе '{chat_title}'.")
            return

        # 4. Реклама/URL — ўчириш
        if contains_advertisement(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Рекламное сообщение удалено в группе '{chat_title}'.")
            return

        # 5. Гуруҳга қўшилганлиги ҳақидаги систем хабар — ўчириш
        if contains_group_join_message(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] '. теперь в группе' ёки қўшилиш хабарини ўчирдик.")
            return

        # 6. Яширин/телеграм линк — ўчириш
        if contains_hidden_link(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Яширин/телеграм ҳаволали хабар ўчирилди ХОНИМ.")
            return

        # 7. Таъқиқланган сўзлар — ўчириш
        if contains_prohibited_words(update):
            await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
            print(f"[{request_counter}] Удалено из-за запрещённых слов.")
            return

        print(f"[{request_counter}] Сообщение не удалено (не от бота, не содержит рекламу или упоминания).")
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")


def main():
    # Создаём приложение
    application = ApplicationBuilder().token(TOKEN).build()

    # 👉 Аввал команда, кейин умумий фильтр
    application.add_handler(CommandHandler("add", add_keyword))
    application.add_handler(MessageHandler(filters.Regex(r"^/\s*add\b"), add_keyword))

    application.add_handler(CommandHandler("show", show_keywords))
    application.add_handler(MessageHandler(filters.Regex(r"^/\s*show\b"), show_keywords))

    application.add_handler(CommandHandler("del", del_keyword))
    application.add_handler(MessageHandler(filters.Regex(r"^/\s*del\b"), del_keyword))

    application.add_handler(CommandHandler("ins", ins_help))
    application.add_handler(MessageHandler(filters.Regex(r"^/\s*ins\b"), ins_help))

    application.add_handler(MessageHandler(filters.ALL, delete_specific_bot_messages))  # ← биттагина ALL қолсин

    async def on_error(update: object, context: CallbackContext) -> None:
        print(f"PTB error: {context.error!r}")

    application.add_error_handler(on_error)

    if FULL_WEBHOOK_URL and is_valid_public_https(FULL_WEBHOOK_URL):
        # Heroku учун Webhook'ни ишга туширамиз
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", 5000)),
            url_path=WEBHOOK_PATH,  # локал роут
            webhook_url=FULL_WEBHOOK_URL,  # ташқи HTTPS
        )
    else:
        print("⚠️ WEBHOOK URL йўқ ёки нотўғри. Polling режимига ўтилди.")
        application.run_polling()


if __name__ == "__main__":
    main()