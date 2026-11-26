# ============================================================
# AIfims.py — BOT 1 GROUP VIDEO + AI MOVIE MATCHING + ORDER
# Uses the existing bot and existing database connection functions.
# All Chat DB: customers, tasks, chat_messages, movies_name,
#              bot_order, bot_order_items
# Movie DB:    items (via get_conn())
# ============================================================

import os, re, json, time, uuid, html, random, logging, threading, unicodedata
from datetime import datetime, timezone
from telebot import types
from telebot.types import ChatPermissions
from psycopg2.extras import RealDictCursor

# ============================================================
# 1. CONFIGURATION
# ============================================================
CLIP_CHANNEL_VIDEO = -1004449824546
CLIP_ADMIN_ID = int(ADMIN_ID)
CLIP_REPORT_ID = AD_REPORT
MOVIE_CHECKER = int(os.getenv("MOVIE_CHECKER", "0"))
CLIP_MAX_SIZE = 50 * 1024 * 1024
CLIP_BAN_SECONDS = 24 * 60 * 60
CLIP_USER_RESTRICTION_SECONDS = 2 * 60 * 60
CLIP_RESULT_CHECK_INTERVAL = 2
CLIP_RESULT_THREAD_STARTED = False
_CLIP_RESULT_LOCK = threading.Lock()
_CLIP_RESULT_DELIVERY_LOCK = threading.Lock()

# Priority list supplied by you. Add more company names here later.
AI_MOVIE_COMPANY_PRIORITY = (
    "Algaita", "Sultan", "Fikira", "Mega", "Gwani",
    "C man", "D love", "Badawa", "PK studio",
)

# Existing main-bot helper expected:
# create_flutterwave_payment(user_id, order_id, amount, display_title)

# ============================================================
# 2. COMMON HELPERS
# ============================================================
def group_clip_user_name(user):
    parts = [getattr(user, "first_name", "") or "", getattr(user, "last_name", "") or ""]
    return " ".join(x.strip() for x in parts if x.strip()) or "Unknown"


def group_clip_username(user):
    return f"@{user.username}" if getattr(user, "username", None) else "Babu username"


def group_clip_safe(value):
    return html.escape(str(value or ""))


def group_clip_json_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}


def group_clip_normalize_words(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()

# ============================================================
# 3. GROUP REPLIES
# ============================================================
GROUP_CLIP_REPLY_MESSAGES = (
    "Malam {name} kaje ka huta ina kan bincika bidiyo dinka zan aika da sakamako a Private Chat🤗",
    "Malam {name} aikinka zan shiga yanzu\nKa duba Private chat ka karbi Complete ba fim din😍",
    "Yallabai {name} Karka damu zan duba wannan gajeren video zan turama cikakken sa A Private chat 😎",
    "Aha naga wannan sakon naka malam {name}\nZan duba video din zan sa maka cikakken sa a Private chat 🥰🙏",
    "Yauwa na ga wannan video din🥳\nKarka damu malam {name} zan bincika shi kuma zan tura maka cikakken a Private chat 🤠",
)


def group_clip_send_random_group_reply(message):
    name = getattr(message.from_user, "first_name", None) or group_clip_user_name(message.from_user) or "Aboki"
    text = random.choice(GROUP_CLIP_REPLY_MESSAGES).format(name=group_clip_safe(name))
    return bot.copy_message(message.chat.id, message.chat.id, message.message_id,
                            caption=f"<b>{text}</b>", parse_mode="HTML",
                            reply_to_message_id=message.message_id)

# ============================================================
# 4. TWO-HOUR RESTRICTION + ADMIN NOTICE
# ============================================================
def group_clip_restrict_user_2_hours(message):
    user, group_id = message.from_user, message.chat.id
    try:
        bot.restrict_chat_member(
            chat_id=group_id, user_id=user.id,
            until_date=int(time.time()) + CLIP_USER_RESTRICTION_SECONDS,
            permissions=ChatPermissions(
                can_send_messages=False, can_send_audios=False,
                can_send_documents=False, can_send_photos=False,
                can_send_videos=False, can_send_video_notes=False,
                can_send_voice_notes=False, can_send_polls=False,
                can_send_other_messages=False, can_add_web_page_previews=False))
        bot.send_message(CLIP_ADMIN_ID,
            "✅ AN DAKATAR DA USER NA TSAYIN 2 HOURS\n━━━━━━━━━━━━━━━━━━━━\n"
            f"User: {group_clip_safe(group_clip_user_name(user))}\n"
            f"User ID: <code>{user.id}</code>\nGroup ID: <code>{group_id}</code>\n"
            f"Message ID: <code>{message.message_id}</code>\n━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
        return True
    except Exception as error:
        logging.exception("GROUP USER 2-HOUR RESTRICTION FAILED")
        try:
            bot.send_message(CLIP_ADMIN_ID,
                "❌ AN KASA DAKATAR DA USER\n"
                f"User: {group_clip_safe(group_clip_user_name(user))}\n"
                f"User ID: <code>{user.id}</code>\nGroup ID: <code>{group_id}</code>\n"
                f"Dalili: {group_clip_safe(str(error)[:2000])}", parse_mode="HTML")
        except Exception:
            logging.exception("RESTRICTION FAILURE ADMIN NOTICE FAILED")
        return False

# ============================================================
# 5. ADMIN /unban USER_ID
# ============================================================
@bot.message_handler(commands=["unban"])
def group_clip_admin_unban(message):
    if not message.from_user or int(message.from_user.id) != CLIP_ADMIN_ID:
        return
    parts = (message.text or "").strip().split()
    if len(parts) != 2:
        bot.reply_to(message, "<b>Amfani:</b>\n/unban USER_ID\n\n<b>Misali:</b>\n/unban 9383838383", parse_mode="HTML")
        return
    try:
        target_id = int(parts[1])
        if target_id <= 0:
            raise ValueError("Invalid user ID")
        bot.restrict_chat_member(
            chat_id=CLIP_CHANNEL_VIDEO, user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=True, can_send_audios=True,
                can_send_documents=True, can_send_photos=True,
                can_send_videos=True, can_send_video_notes=True,
                can_send_voice_notes=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True))
        bot.reply_to(message,
            "<b>✅ AN BUƊE USER NASARA!</b>\n"
            f"User ID: <code>{target_id}</code>\nGroup ID: <code>{CLIP_CHANNEL_VIDEO}</code>", parse_mode="HTML")
    except ValueError:
        bot.reply_to(message, "<b>❌ User ID bai dace ba.</b>\nMisali: /unban 9383838383", parse_mode="HTML")
    except Exception as error:
        logging.exception("ADMIN UNBAN COMMAND FAILED")
        bot.reply_to(message, f"<b>❌ AN KASA BUƊE USER</b>\n{group_clip_safe(str(error)[:2000])}", parse_mode="HTML")

# ============================================================
# 6. FILTER + VIDEO DETECTION
# ============================================================
def group_clip_is_valid(message):
    return bool(message and message.chat and message.chat.id == CLIP_CHANNEL_VIDEO
                and message.chat.type in ("group", "supergroup")
                and message.from_user and not message.from_user.is_bot
                and int(message.from_user.id) != CLIP_ADMIN_ID)


def group_clip_get_video(message):
    if message.video:
        item = message.video
        return {"file_id": item.file_id, "file_unique_id": item.file_unique_id,
                "file_size": int(item.file_size or 0), "file_name": None,
                "mime_type": item.mime_type or "video/mp4", "file_type": "video"}
    if message.document and (message.document.mime_type or "").lower().startswith("video/"):
        item = message.document
        return {"file_id": item.file_id, "file_unique_id": item.file_unique_id,
                "file_size": int(item.file_size or 0), "file_name": item.file_name,
                "mime_type": item.mime_type, "file_type": "document_video"}
    return None


def group_clip_oversize_video(message):
    try:
        bot.copy_message(message.from_user.id, message.chat.id, message.message_id)
        bot.send_message(message.from_user.id,
            "<b>Wannan Video da ka tura a group yayi girma.</b>\n"
            "Bani da izinin sarrafa video da ya wuce 50MB.\n\n"
            "Ka rage girmansa ka sake aiko shi a Group din☺️\n\nMun gode.", parse_mode="HTML")
    except Exception:
        logging.exception("OVERSIZE VIDEO USER DM FAILED")
    finally:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except Exception:
            logging.exception("OVERSIZE VIDEO GROUP DELETE FAILED")
    return False

# ============================================================
# 7. ADULT CAPTION PROTECTION
# ============================================================
GROUP_CLIP_ADULT_KEYWORDS = (
    "porn", "porno", "pornography", "xxx", "sex", "sexual", "sex video", "sex film",
    "adult", "adult video", "adult movie", "nude", "nudes", "nudity", "naked", "erotic",
    "hentai", "blowjob", "handjob", "onlyfans", "milf", "rape", "incest", "orgasm",
    "masturbation", "batsa", "tsiraici", "iskanci", "karuwanci", "lalata",
    "bidiyon batsa", "hotunan batsa", "finafinan batsa", "fim din batsa")


def group_clip_normalize_caption(caption):
    value = unicodedata.normalize("NFKC", caption or "").lower()
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    for old, new in {"@":"a", "0":"o", "1":"i", "!":"i", "3":"e", "4":"a", "5":"s", "$":"s", "7":"t", "8":"b"}.items():
        value = value.replace(old, new)
    return re.sub(r"[^a-z0-9]+", "", value)


def group_clip_is_adult_caption(caption):
    normalized = group_clip_normalize_caption(caption)
    return any(group_clip_normalize_caption(word) in normalized for word in GROUP_CLIP_ADULT_KEYWORDS)


def group_clip_send_report(message, video_info):
    user = message.from_user
    report = ("🚨 GROUP VIDEO CONTENT REPORT\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Name: {group_clip_user_name(user)}\nUsername: {group_clip_username(user)}\n"
        f"User ID: {user.id}\nGroup ID: {message.chat.id}\nMessage ID: {message.message_id}\n"
        f"File Size: {video_info['file_size']}\nFile Name: {video_info['file_name'] or 'Unknown'}\n"
        f"File Unique ID: {video_info['file_unique_id']}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Original Caption:\n{message.caption or 'No caption'}\n━━━━━━━━━━━━━━━━━━━━\n"
        f"Report Time: {datetime.now(timezone.utc).isoformat()}")
    try:
        bot.copy_message(CLIP_REPORT_ID, message.chat.id, message.message_id)
    except Exception:
        logging.exception("ADULT REPORT VIDEO COPY FAILED")
    bot.send_message(CLIP_REPORT_ID, report[:3900])


def group_clip_remove_and_restrict(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        logging.exception("ADULT MESSAGE DELETE FAILED")
    try:
        bot.restrict_chat_member(
            chat_id=message.chat.id, user_id=message.from_user.id,
            until_date=int(time.time()) + CLIP_BAN_SECONDS,
            permissions=ChatPermissions(
                can_send_messages=False, can_send_audios=False, can_send_documents=False,
                can_send_photos=False, can_send_videos=False, can_send_video_notes=False,
                can_send_voice_notes=False, can_send_polls=False,
                can_send_other_messages=False, can_add_web_page_previews=False))
    except Exception:
        logging.exception("24-HOUR RESTRICTION FAILED")

# ============================================================
# 8. DM ACKNOWLEDGEMENT + FAILURE NOTICE
# ============================================================
def group_clip_send_acknowledgement(message):
    return bot.copy_message(
        chat_id=message.from_user.id, from_chat_id=message.chat.id,
        message_id=message.message_id,
        caption="<b>MADALLA NA KARBI BIDIYONKA INA BINCIKAWA 😊</b>\n\n"
                "<b>Dan Allah ka jira idan na samu video din zan sanar da kai🤗</b>",
        parse_mode="HTML")


def group_clip_private_message_failed(message):
    user = message.from_user
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        logging.exception("FAILED TO DELETE GROUP VIDEO")
    mention = f'<a href="tg://user?id={user.id}">{group_clip_safe(group_clip_user_name(user))}</a>'
    try:
        bot.send_message(message.chat.id,
            f"<b>Yi hakuri malam {mention}</b>\n\n"
            "<b>Aikin ka bazai kammala ba.\nDa bukatar kaje AlgaitaBot ka taba &lt;start&gt;.\n"
            "Sannan kazo ka turo video din anan group.\n\nMun gode🙏</b>", parse_mode="HTML")
    except Exception:
        logging.exception("PRIVATE MESSAGE FAILURE NOTICE FAILED")

# ============================================================
# 9. TASK CREATION — ALL CHAT DB
# ack_message_id is saved for deleting the checking message later.
# ============================================================
def group_clip_create_task(message, video_info, ack_message):
    user = message.from_user
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM chat_messages WHERE telegram_chat_id=%s AND telegram_message_id=%s LIMIT 1",
                    (message.chat.id, message.message_id))
        if cur.fetchone():
            conn.rollback()
            return None
        cur.execute("""
            INSERT INTO customers (user_id, username, first_name, last_name,
                first_seen_at, last_interaction_at, total_messages, updated_at)
            VALUES (%s,%s,%s,%s,NOW(),NOW(),1,NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                username=EXCLUDED.username, first_name=EXCLUDED.first_name,
                last_name=EXCLUDED.last_name, last_interaction_at=NOW(),
                total_messages=customers.total_messages+1, updated_at=NOW()
        """, (user.id, user.username, user.first_name, user.last_name))
        payload = {
            "source":"telegram_group", "telegram_chat_id":message.chat.id,
            "telegram_message_id":message.message_id, "file_id_bot1":video_info["file_id"],
            "file_unique_id":video_info["file_unique_id"], "file_size":video_info["file_size"],
            "file_name":video_info["file_name"], "mime_type":video_info["mime_type"],
            "file_type":video_info["file_type"], "caption":message.caption or "",
            "username":user.username, "first_name":user.first_name, "last_name":user.last_name,
            "user_id":user.id, "ack_chat_id":user.id, "ack_message_id":ack_message.message_id,
            "bot1_delivered":False, "movie_order_created":False}
        cur.execute("""
            INSERT INTO tasks (user_id,task_type,status,priority,payload)
            VALUES (%s,'movie_identification','pending',5,%s::jsonb) RETURNING task_id
        """, (user.id, json.dumps(payload)))
        task_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO chat_messages (user_id,task_id,telegram_chat_id,telegram_message_id,
                direction,sender_type,message_type,content,file_id,file_unique_id,file_name,
                mime_type,file_size,language_code)
            VALUES (%s,%s,%s,%s,'incoming','user','video',%s,%s,%s,%s,%s,%s,%s)
        """, (user.id,task_id,message.chat.id,message.message_id,message.caption or "",
              video_info["file_id"],video_info["file_unique_id"],video_info["file_name"],
              video_info["mime_type"],video_info["file_size"],getattr(user,"language_code",None)))
        conn.commit()
        logging.info("GROUP VIDEO TASK CREATED: %s", task_id)
        return str(task_id)
    except Exception:
        conn.rollback()
        logging.exception("GROUP VIDEO TASK CREATION FAILED")
        raise
    finally:
        if cur: cur.close()
        conn.close()

# ============================================================
# 10. AI RESULT EXTRACTION
# ============================================================
def group_clip_extract_ai_movie(result):
    result = group_clip_json_dict(result)
    title = result.get("movie_title") or result.get("title") or result.get("film_title") or result.get("movie")
    year = result.get("movie_year") or result.get("year") or result.get("release_year")
    if isinstance(title, dict):
        title = title.get("title") or title.get("name")
    title = str(title or "").strip()
    if not title:
        raise ValueError("AI result bai ƙunshi movie title ba.")
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(year or ""))
    if not match:
        match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
    if not match:
        raise ValueError("AI result bai ƙunshi shekarar fim ba.")
    release_year = int(match.group(1))
    clean_title = re.sub(r"\s*\(?\b(19\d{2}|20\d{2})\b\)?\s*$", "", title).strip() or title
    return clean_title, release_year

# ============================================================
# 11. ORIGINAL MOVIE NAME SEARCH — ALL CHAT DB
# Exact title/year first; normalized title fallback still requires same year.
# ============================================================
def group_clip_find_movie_group_keys(original_title, release_year):
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT group_key,original_title,release_year FROM movies_name
            WHERE release_year=%s AND LOWER(TRIM(original_title))=LOWER(TRIM(%s))
            ORDER BY id ASC
        """, (int(release_year), original_title))
        rows = cur.fetchall()
        if not rows:
            cur.execute("SELECT group_key,original_title,release_year FROM movies_name WHERE release_year=%s ORDER BY id ASC",
                        (int(release_year),))
            rows = [r for r in cur.fetchall()
                    if group_clip_normalize_words(r["original_title"]) == group_clip_normalize_words(original_title)]
        output, seen = [], set()
        for row in rows:
            key = row.get("group_key")
            if key and key not in seen:
                seen.add(key)
                output.append({"group_key":key,"original_title":row.get("original_title"),"release_year":row.get("release_year")})
        return output
    finally:
        if cur: cur.close()
        conn.close()

# ============================================================
# 12. ITEMS SEARCH — MOVIE DB (get_conn), NOT ALL CHAT DB
# ============================================================
def group_clip_fetch_items_for_group_keys(group_keys):
    if not group_keys:
        return []
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id,title,price,file_id,group_key FROM items
            WHERE group_key = ANY(%s) ORDER BY id ASC
        """, (list(group_keys),))
        return cur.fetchall()
    finally:
        if cur: cur.close()
        conn.close()

# ============================================================
# 13. COMPANY DETECTION + PRIORITY
# One group => use it directly. Multiple => company priority.
# No company match => earliest item inserted wins.
# ============================================================
def group_clip_detect_company(title):
    # Parenthesized company tags take precedence. Example:
    # "Mega Love (Sultan)" must be detected as Sultan, not Mega.
    parenthetical = re.findall(r"\(([^()]*)\)", str(title or ""))
    for section in parenthetical:
        normalized_section = f" {group_clip_normalize_words(section)} "
        for company in AI_MOVIE_COMPANY_PRIORITY:
            token = f" {group_clip_normalize_words(company)} "
            if token.strip() and token in normalized_section:
                return company

    # Otherwise detect a whole company token anywhere in the admin title,
    # including before or after the year.
    normalized = f" {group_clip_normalize_words(title)} "
    for company in AI_MOVIE_COMPANY_PRIORITY:
        token = f" {group_clip_normalize_words(company)} "
        if token.strip() and token in normalized:
            return company
    return None


def group_clip_select_movie_group(group_rows, item_rows):
    by_group = {}
    for item in item_rows:
        if item.get("group_key"):
            by_group.setdefault(item["group_key"], []).append(item)
    candidates = []
    for movie in group_rows:
        key = movie["group_key"]
        usable = [x for x in by_group.get(key, []) if x.get("file_id")]
        if usable:
            candidates.append({"group_key":key,"items":sorted(usable,key=lambda x:int(x["id"])),
                               "first_item_id":min(int(x["id"]) for x in usable),"company":None})
    if not candidates:
        return None, "no_files"
    if len(candidates) == 1:
        return candidates[0], "single_match"
    for candidate in candidates:
        matches = [group_clip_detect_company(x.get("title") or "") for x in candidate["items"]]
        matches = [x for x in matches if x]
        if matches:
            candidate["company"] = min(matches,key=lambda x:AI_MOVIE_COMPANY_PRIORITY.index(x))
    ranked = [x for x in candidates if x["company"]]
    if ranked:
        return min(ranked,key=lambda x:(AI_MOVIE_COMPANY_PRIORITY.index(x["company"]),x["first_item_id"])), "company_priority"
    return min(candidates,key=lambda x:x["first_item_id"]), "earliest_inserted"

# ============================================================
# 14. CREATE ORDER — ALL CHAT DB
# One bot_order per movie group; all files in bot_order_items.
# Price is charged once per group, not once per file.
# No user_movies check: repeat purchases are allowed.
# ============================================================
def group_clip_create_ai_order(task_id,user_id,selected_movie,movie_title,movie_year):
    selected_items = sorted(selected_movie["items"],key=lambda x:int(x["id"]))
    if not selected_items:
        raise ValueError("Selected movie group has no file_id.")
    first_item = selected_items[0]
    total = int(first_item.get("price") or 0)
    if total <= 0:
        raise ValueError("Farashin fim bai dace ba.")
    order_id = str(uuid.uuid4())
    group_key = str(selected_movie["group_key"])
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id,amount FROM bot_order WHERE task_id=%s ORDER BY created_at DESC LIMIT 1",(str(task_id),))
        existing = cur.fetchone()
        if existing:
            conn.commit()
            return str(existing[0]),int(existing[1]),selected_items
        cur.execute("""
            INSERT INTO bot_order (id,user_id,movie_id,item_id,amount,paid,pay_ref,type,
                task_id,group_key,selected_movie_title,selected_movie_year)
            VALUES (%s,%s,NULL,%s,%s,0,NULL,'AI order',%s,%s,%s,%s)
        """,(order_id,int(user_id),int(first_item["id"]),total,str(task_id),group_key,movie_title,int(movie_year)))
        for item in selected_items:
            cur.execute("""
                INSERT INTO bot_order_items(order_id,item_id,file_id,price)
                VALUES(%s,%s,%s,%s) ON CONFLICT(order_id,item_id) DO NOTHING
            """,(order_id,int(item["id"]),item["file_id"],int(item.get("price") or total)))
        cur.execute("""
            UPDATE tasks SET payload=COALESCE(payload,'{}'::jsonb)||%s::jsonb,updated_at=NOW()
            WHERE task_id=%s
        """,(json.dumps({"movie_order_created":True,"bot_order_id":order_id,
                           "selected_group_key":group_key,"selected_movie_title":movie_title,
                           "selected_movie_year":int(movie_year)}),str(task_id)))
        conn.commit()
        return order_id,total,selected_items
    except Exception:
        conn.rollback()
        logging.exception("AI BOT ORDER CREATION FAILED")
        raise
    finally:
        if cur: cur.close()
        conn.close()

# ============================================================
# 15. FLUTTERWAVE PAYMENT URL
# ============================================================
def group_clip_extract_payment_url(result):
    if isinstance(result,str): return result.strip()
    if isinstance(result,dict):
        for key in ("payment_url","link","url","checkout_url"):
            if result.get(key): return str(result[key]).strip()
    return None


def group_clip_create_payment_link(user_id,order_id,amount,display_title):
    helper = globals().get("create_flutterwave_payment")
    if not callable(helper):
        raise RuntimeError("create_flutterwave_payment() bai samu ba a main bot.")
    result = helper(int(user_id),str(order_id),int(amount),str(display_title))
    url = group_clip_extract_payment_url(result)
    if not url:
        raise RuntimeError("Flutterwave helper bai dawo da payment URL da aka gane ba.")
    return url

# ============================================================
# 16. MOVIE CHECKER — SEND USER VIDEO + PENDING + CHANGE BUTTON
# Save checker_chat_id and checker_message_id in bot_order.
# ============================================================
def group_clip_checker_caption(payload,movie_title,movie_year,order_id):
    full_name = (str(payload.get("first_name") or "")+" "+str(payload.get("last_name") or "")).strip() or "Unknown"
    username = "@"+str(payload["username"]) if payload.get("username") else "No username"
    return ("<b>🎬 AI MOVIE ORDER — PENDING</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>User:</b> {group_clip_safe(full_name)}\n<b>Username:</b> {group_clip_safe(username)}\n"
        f"<b>User ID:</b> <code>{int(payload.get('user_id') or 0)}</code>\n"
        f"<b>Movie:</b> {group_clip_safe(movie_title)}\n<b>Year:</b> {int(movie_year)}\n"
        f"<b>Order ID:</b> <code>{group_clip_safe(order_id)}</code>\n"
        "<b>Status:</b> ⏳ PENDING ORDER\n━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Admin: ka duba ko fim din da aka zaba shi ne daidai.</i>")


def group_clip_send_checker_pending(payload,order_id,movie_title,movie_year):
    if not MOVIE_CHECKER:
        raise RuntimeError("Saita MOVIE_CHECKER da real group ID a environment variables.")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔄 Change Movie",callback_data=f"ai_change_movie:{order_id}"))
    sent = bot.copy_message(
        chat_id=MOVIE_CHECKER,from_chat_id=int(payload["telegram_chat_id"]),
        message_id=int(payload["telegram_message_id"]),
        caption=group_clip_checker_caption(payload,movie_title,movie_year,order_id),
        parse_mode="HTML",reply_markup=keyboard)
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE bot_order SET checker_chat_id=%s,checker_message_id=%s WHERE id=%s",
                    (MOVIE_CHECKER,sent.message_id,str(order_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        logging.exception("FAILED TO SAVE CHECKER MESSAGE IDS")
        raise
    finally:
        if cur: cur.close()
        conn.close()
    return sent

# ============================================================
# 17. SEND PAYMENT LINK TO CUSTOMER
# ============================================================
def group_clip_send_payment_to_user(user_id,order_id,amount,movie_title,movie_year,payment_url):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("💳 Pay Now",url=payment_url))
    text = ("<b>🎬 AN SAMU FIM ƊINKA!</b>\n\n"
        f"<b>Movie:</b> {group_clip_safe(movie_title)}\n<b>Year:</b> {int(movie_year)}\n"
        f"<b>Amount:</b> ₦{int(amount):,}\n<b>Order ID:</b> <code>{group_clip_safe(order_id)}</code>\n\n"
        "Danna Pay Now domin biyan kuɗi. Bayan an tabbatar da biyan kuɗi za a kammala maka order ɗinka.\n\n"
        "<i>Mun gode da amfani da AlgaitaBot 🙏</i>")
    return bot.send_message(int(user_id),text,parse_mode="HTML",reply_markup=keyboard)

# ============================================================
# 18. PROCESS AI RESULT — LOOKUP -> SELECT -> ORDER -> CHECKER -> PAY
# ============================================================
def group_clip_process_completed_task(task_id,payload,result_json):
    payload = group_clip_json_dict(payload)
    result_json = group_clip_json_dict(result_json)
    if not payload or not result_json:
        raise ValueError("Task payload/result_json babu ko ba su dace ba.")
    user_id = int(payload["user_id"])

    # Recovery/idempotency: do not create another order for this task.
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bot_order WHERE task_id=%s LIMIT 1",(str(task_id),))
        existing = cur.fetchone()
    finally:
        if cur: cur.close()
        conn.close()
    if existing:
        logging.info("ORDER ALREADY EXISTS FOR TASK %s",task_id)
        return

    movie_title,movie_year = group_clip_extract_ai_movie(result_json)
    # movies_name is in All Chat DB.
    movie_groups = group_clip_find_movie_group_keys(movie_title,movie_year)
    if not movie_groups:
        raise LookupError(f"Ba a samu '{movie_title}' ({movie_year}) a movies_name ba.")
    # items is in the separate Movie DB.
    group_keys = [x["group_key"] for x in movie_groups]
    items = group_clip_fetch_items_for_group_keys(group_keys)
    selected,reason = group_clip_select_movie_group(movie_groups,items)
    if not selected:
        raise LookupError("An samu original movie name amma babu file mai file_id a items.")
    logging.info("AI MOVIE CHOSEN title=%s year=%s group=%s reason=%s company=%s",
                 movie_title,movie_year,selected["group_key"],reason,selected.get("company"))

    # Create one All Chat DB order and link every file through bot_order_items.
    order_id,amount,selected_items = group_clip_create_ai_order(
        task_id,user_id,selected,movie_title,movie_year)

    # Remove the earlier checking message from user's DM using saved ID.
    try:
        bot.delete_message(chat_id=int(payload.get("ack_chat_id") or user_id),
                           message_id=int(payload["ack_message_id"]))
    except Exception:
        logging.exception("FAILED TO DELETE OLD INA BINCIKAWA MESSAGE task=%s",task_id)

    # Send submitted video to MOVIE_CHECKER with Pending + Change Movie.
    checker_message = group_clip_send_checker_pending(payload,order_id,movie_title,movie_year)

    # Create Flutterwave link and send it to the customer.
    payment_url = group_clip_create_payment_link(user_id,order_id,amount,f"{movie_title} ({movie_year})")
    group_clip_send_payment_to_user(user_id,order_id,amount,movie_title,movie_year,payment_url)

    # Mark task delivered only after successful checker and user delivery.
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE tasks SET payload=COALESCE(payload,'{}'::jsonb)||%s::jsonb,updated_at=NOW()
            WHERE task_id=%s
        """,(json.dumps({"bot1_delivered":True,"movie_order_created":True,
                           "bot_order_id":order_id,"checker_message_id":checker_message.message_id,
                           "checker_chat_id":MOVIE_CHECKER}),str(task_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        logging.exception("FAILED TO MARK TASK DELIVERED %s",task_id)
        raise
    finally:
        if cur: cur.close()
        conn.close()
    logging.info("AI MOVIE ORDER SENT: task=%s order=%s",task_id,order_id)

# ============================================================
# 19. COMPLETED TASK POLLER — EVERY TWO SECONDS
# ============================================================
def group_clip_check_completed_tasks():
    if not _CLIP_RESULT_DELIVERY_LOCK.acquire(blocking=False):
        return
    try:
        conn = get_all_chat_db_conn()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT task_id,payload,result_json FROM tasks
                WHERE status='completed' AND task_type='movie_identification'
                  AND COALESCE(payload->>'bot1_delivered','false')!='true'
                ORDER BY completed_at ASC NULLS LAST,created_at ASC LIMIT 100
            """)
            rows = cur.fetchall()
        finally:
            if cur: cur.close()
            conn.close()
        for task_id,payload,result_json in rows:
            try:
                group_clip_process_completed_task(task_id,payload,result_json)
            except LookupError as error:
                logging.warning("AI MOVIE NOT FOUND — TASK %s: %s",task_id,error)
            except Exception:
                logging.exception("AI MOVIE ORDER PROCESSING FAILED task=%s",task_id)
    finally:
        _CLIP_RESULT_DELIVERY_LOCK.release()


def group_clip_result_worker():
    logging.info("AIFIMS RESULT WORKER STARTED — CHECK EVERY 2 SECONDS")
    while True:
        try:
            group_clip_check_completed_tasks()
        except Exception:
            logging.exception("AIFIMS RESULT WORKER ERROR — WILL RETRY")
        time.sleep(CLIP_RESULT_CHECK_INTERVAL)


def group_clip_start_result_worker():
    global CLIP_RESULT_THREAD_STARTED
    with _CLIP_RESULT_LOCK:
        if CLIP_RESULT_THREAD_STARTED:
            return
        threading.Thread(target=group_clip_result_worker,daemon=True,name="AIfimsResultWorker").start()
        CLIP_RESULT_THREAD_STARTED = True
        logging.info("AIFIMS RESULT WORKER STARTED")

# ============================================================
# 20. CHANGE MOVIE BUTTON — ADMIN-ONLY PLACEHOLDER
# The button and message IDs are stored. Full replacement workflow
# needs the admin's chosen new title/year and is intentionally not
# guessed here. This callback verifies the order and its unpaid state.
# ============================================================
@bot.callback_query_handler(func=lambda call: bool(call.data and call.data.startswith("ai_change_movie:")))
def group_clip_admin_change_movie_callback(call):
    try:
        if not call.from_user or int(call.from_user.id) != CLIP_ADMIN_ID:
            bot.answer_callback_query(call.id,"Wannan aikin na admin ne kawai.",show_alert=True)
            return
        order_id = call.data.split(":",1)[1].strip()
        conn = get_all_chat_db_conn()
        cur = None
        try:
            cur = conn.cursor()
            cur.execute("SELECT paid,checker_chat_id,checker_message_id,selected_movie_title,selected_movie_year FROM bot_order WHERE id=%s",(order_id,))
            row = cur.fetchone()
        finally:
            if cur: cur.close()
            conn.close()
        if not row:
            bot.answer_callback_query(call.id,"Ba a samu order din ba.",show_alert=True)
        elif int(row[0] or 0) == 1:
            bot.answer_callback_query(call.id,"An riga an biya. Ba za a iya canza fim ba.",show_alert=True)
        else:
            bot.answer_callback_query(call.id,"An gano order. An adana message ID domin tsarin Change Movie.",show_alert=True)
            logging.info("ADMIN CHANGE MOVIE CLICK order=%s checker_chat=%s message=%s",order_id,row[1],row[2])
    except Exception:
        logging.exception("CHANGE MOVIE CALLBACK FAILED")
        try: bot.answer_callback_query(call.id,"An samu matsala.",show_alert=True)
        except Exception: pass

# ============================================================
# 21. MARK ORDER PAID — CALL FROM VERIFIED FLUTTERWAVE WEBHOOK
# Never call this merely because user clicked Pay Now.
# Updates bot_order.paid and edits the saved checker caption to PAID,
# removing the Change Movie button.
# ============================================================
def group_clip_mark_ai_order_paid(order_id,verified_reference=None):
    conn = get_all_chat_db_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT checker_chat_id,checker_message_id,user_id,selected_movie_title,
                   selected_movie_year,paid FROM bot_order WHERE id=%s LIMIT 1
        """,(str(order_id),))
        row = cur.fetchone()
        if not row:
            raise LookupError(f"AI order not found: {order_id}")
        checker_chat_id,checker_message_id,user_id,title,year,paid = row
        if int(paid or 0) == 1:
            conn.commit()
            return True
        cur.execute("UPDATE bot_order SET paid=1,pay_ref=COALESCE(%s,pay_ref) WHERE id=%s",
                    (verified_reference,str(order_id)))
        conn.commit()
    except Exception:
        conn.rollback()
        logging.exception("AI ORDER PAID UPDATE FAILED")
        raise
    finally:
        if cur: cur.close()
        conn.close()
    if checker_chat_id and checker_message_id:
        try:
            caption = ("<b>🎬 AI MOVIE ORDER</b>\n━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Movie:</b> {group_clip_safe(title)}\n<b>Year:</b> {int(year or 0)}\n"
                f"<b>User ID:</b> <code>{int(user_id or 0)}</code>\n"
                f"<b>Order ID:</b> <code>{group_clip_safe(order_id)}</code>\n"
                "<b>Status:</b> ✅ PAID\n━━━━━━━━━━━━━━━━━━━━")
            bot.edit_message_caption(chat_id=int(checker_chat_id),message_id=int(checker_message_id),
                                     caption=caption,parse_mode="HTML",reply_markup=None)
        except Exception:
            logging.exception("ORDER PAID BUT CHECKER MESSAGE EDIT FAILED order=%s",order_id)
    return True

# ============================================================
# 22. MAIN GROUP VIDEO RECEIVER — ORIGINAL FLOW PRESERVED
# ============================================================
@bot.message_handler(content_types=["video","document"],func=lambda message: group_clip_is_valid(message))
def bot1_group_video_receiver(message):
    try:
        video_info = group_clip_get_video(message)
        if not video_info or video_info["file_size"] <= 0:
            return
        # 1. Size protection
        if video_info["file_size"] > CLIP_MAX_SIZE:
            group_clip_oversize_video(message)
            return
        # 2. Caption protection
        if group_clip_is_adult_caption(message.caption or ""):
            try: group_clip_send_report(message,video_info)
            except Exception: logging.exception("ADULT REPORT FAILED")
            group_clip_remove_and_restrict(message)
            return
        # 3. Send original video + checking caption to user DM
        try:
            ack_message = group_clip_send_acknowledgement(message)
        except Exception:
            logging.exception("CANNOT SEND ACKNOWLEDGEMENT")
            group_clip_private_message_failed(message)
            return
        # 4. Save customer/task/message IDs in All Chat DB
        try:
            task_id = group_clip_create_task(message,video_info,ack_message)
            if not task_id:
                logging.warning("DUPLICATE GROUP VIDEO MESSAGE %s",message.message_id)
                return
            logging.info("GROUP VIDEO ACCEPTED TASK=%s",task_id)
        except Exception:
            logging.exception("GROUP VIDEO TASK SAVE FAILED")
            try:
                bot.edit_message_caption(chat_id=message.from_user.id,message_id=ack_message.message_id,
                    caption="<b>Yi hakuri, an samu matsala wajen ajiye bidiyonka.\nDon Allah ka sake gwadawa anjima.</b>",parse_mode="HTML")
            except Exception: logging.exception("TASK FAILURE NOTICE FAILED")
            return
        # 5. Random group reply
        try: group_clip_send_random_group_reply(message)
        except Exception: logging.exception("RANDOM GROUP REPLY FAILED")
        # 6. Two-hour restriction + admin notice
        group_clip_restrict_user_2_hours(message)
    except Exception:
        logging.exception("UNHANDLED MAIN VIDEO HANDLER ERROR")
        raise

# ============================================================
# 23. START WORKER ONCE AFTER BOT INITIALIZATION
# ============================================================
group_clip_start_result_worker()

# ============================================================
# END AIfims.py
# ============================================================
