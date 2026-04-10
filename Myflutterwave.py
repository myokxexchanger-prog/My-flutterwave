

## bot.py  (PostgreSQL SAFE – FULL FIX, nothing removed)

import telebot
from telebot import types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import psycopg2
import time
import os

# ======================
# DATABASE CONNECTION
# ======================
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")
    
def get_conn():
    try:
        c = psycopg2.connect(
            DATABASE_URL,
            connect_timeout=5,
            sslmode="require"
        )
        c.autocommit = True
        return c
    except Exception as e:
        print("❌ DB CONNECT ERROR:", e)
        return None
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()
# =========================================
# ======================
# WALLET DATABASE CONNECTION
# ======================
WALLET_DATABASE_URL = os.environ.get("WALLET_DATABASE_URL")

if not WALLET_DATABASE_URL:
    raise RuntimeError("WALLET_DATABASE_URL is not set")

def get_wallet_conn():
    try:
        c = psycopg2.connect(
            WALLET_DATABASE_URL,
            connect_timeout=5,
            sslmode="require"
        )
        c.autocommit = True
        return c
    except Exception as e:
        print("❌ WALLET DB CONNECT ERROR:", e)
        return None

# ===== GLOBAL CONNECTION (FOR TABLE CREATION) =====
wallet_conn = psycopg2.connect(WALLET_DATABASE_URL)
wallet_conn.autocommit = True
wallet_cur = wallet_conn.cursor()


# AUTO DB FIX: ENSURE invite_link COLUMN
# ==========================================
def ensure_vip_invite_column():
    try:
        conn = get_conn()
        cur = conn.cursor()

        # Check if column exists
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='vip_members'
            AND column_name='invite_link'
        """)
        exists = cur.fetchone()

        if not exists:
            cur.execute("""
                ALTER TABLE vip_members
                ADD COLUMN invite_link TEXT DEFAULT NULL
            """)
            conn.commit()

            try:
                bot.send_message(ADMIN_ID, "✅ invite_link column created successfully.")
            except:
                pass
        else:
            try:
                bot.send_message(ADMIN_ID, "ℹ invite_link column already exists.")
            except:
                pass

        cur.close()
        conn.close()

    except Exception as e:
        try:
            bot.send_message(ADMIN_ID, f"❌ DB AUTO FIX ERROR:\n{e}")
        except:
            pass


# Run immediately on startup
ensure_vip_invite_column()


# ============================================
# VIP TABLE AUTO STRUCTURE FIX (RUN ON START)
# ============================================

def ensure_vip_table_structure():
    try:
        conn = get_conn()
        cur = conn.cursor()

        print("🔍 Checking VIP table structure...")

        # ================= CHECK TABLE =================
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'vip_members'
            )
        """)
        table_exists = cur.fetchone()[0]

        if not table_exists:
            print("⚠️ vip_members table not found. Creating it...")

            cur.execute("""
                CREATE TABLE vip_members (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT UNIQUE NOT NULL,
                    order_id TEXT,
                    join_date TIMESTAMP,
                    expire_at TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    warn1_sent BOOLEAN DEFAULT FALSE,
                    warn2_sent BOOLEAN DEFAULT FALSE,
                    payment_date TIMESTAMP DEFAULT NOW()
                )
            """)

            conn.commit()
            print("✅ vip_members table created.")

        else:
            print("✅ vip_members table exists. Checking columns...")

            # ================= CHECK COLUMNS =================
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='vip_members'
            """)
            existing_cols = [r[0] for r in cur.fetchall()]

            def add_column(query, col_name):
                if col_name not in existing_cols:
                    print(f"⚠️ Adding missing column: {col_name}")
                    cur.execute(query)

            add_column(
                "ALTER TABLE vip_members ADD COLUMN order_id TEXT",
                "order_id"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN join_date TIMESTAMP",
                "join_date"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN expire_at TIMESTAMP",
                "expire_at"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN status TEXT DEFAULT 'active'",
                "status"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN warn1_sent BOOLEAN DEFAULT FALSE",
                "warn1_sent"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN warn2_sent BOOLEAN DEFAULT FALSE",
                "warn2_sent"
            )

            add_column(
                "ALTER TABLE vip_members ADD COLUMN payment_date TIMESTAMP DEFAULT NOW()",
                "payment_date"
            )

            conn.commit()
            print("✅ VIP table structure verified.")

        cur.close()
        conn.close()

    except Exception as e:
        print("❌ VIP STRUCTURE CHECK FAILED:", e)


# Run automatically when app starts
ensure_vip_table_structure()


# =============================
# ENSURE VIP MEMBERS TABLE
# =============================
def ensure_vip_members_table():
    try:
        # 1️⃣ Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vip_members (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL
            )
        """)

        # 2️⃣ Ensure order_id column
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='vip_members'
            AND column_name='order_id'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE vip_members ADD COLUMN order_id TEXT")

        # 3️⃣ Ensure join_date column
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='vip_members'
            AND column_name='join_date'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE vip_members ADD COLUMN join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # 4️⃣ Ensure expire_at column
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='vip_members'
            AND column_name='expire_at'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE vip_members ADD COLUMN expire_at TIMESTAMP")

        # 5️⃣ Ensure status column
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='vip_members'
            AND column_name='status'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE vip_members ADD COLUMN status VARCHAR(20) DEFAULT 'active'")

        print("✅ vip_members table structure verified")

    except Exception as e:
        print("❌ VIP MEMBERS MIGRATION ERROR:", e)


# 🔥 Run at startup
ensure_vip_members_table()
# =============================
# ENSURE VIP MEMBERS TABLE
# =============================
def ensure_vip_members_table():
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vip_members (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL
            )
        """)

        # Helper function
        def ensure_column(column_name, column_type):
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name='vip_members'
                AND column_name=%s
            """, (column_name,))
            if not cur.fetchone():
                cur.execute(f"ALTER TABLE vip_members ADD COLUMN {column_name} {column_type}")

        # Required columns
        ensure_column("order_id", "TEXT")
        ensure_column("join_date", "TIMESTAMP")
        ensure_column("expire_at", "TIMESTAMP")
        ensure_column("status", "VARCHAR(20) DEFAULT 'active'")
        ensure_column("warn1_sent", "BOOLEAN DEFAULT FALSE")
        ensure_column("warn2_sent", "BOOLEAN DEFAULT FALSE")
        ensure_column("payment_date", "TIMESTAMP")

        print("✅ vip_members table structure verified")

    except Exception as e:
        print("❌ VIP MEMBERS MIGRATION ERROR:", e)

# =============================
# ENSURE ORDERS TABLE STRUCTURE
# =============================
def ensure_orders_columns():
    try:
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='orders'
              AND column_name='type'
        """)
        exists = cur.fetchone()

        if not exists:
            cur.execute("ALTER TABLE orders ADD COLUMN type VARCHAR(20) DEFAULT 'film'")
            print("✅ Column 'type' added successfully")
        else:
            print("✅ Column 'type' already exists")

    except Exception as e:
        print("❌ MIGRATION ERROR:", e)


# 🔥 Run migration once at startup
ensure_orders_columns()




# ======================
# GLOBAL STATES
# ======================
TRANSFER_STAGE = {}
admin_states = {}
last_menu_msg = {}
last_category_msg = {}
last_allfilms_msg = {}
allfilms_sessions = {}
cart_sessions = {}
series_sessions = {}
user_states = {}
active_links = {}


# =========================
# WALLET DATABASE TABLES
# =========================

# -------- WALLET BALANCE --------
wallet_cur.execute("""
CREATE TABLE IF NOT EXISTS wallet_balance (
    user_id BIGINT PRIMARY KEY,
    balance BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------- WALLET TRANSACTIONS --------
wallet_cur.execute("""
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount BIGINT NOT NULL,
    type VARCHAR(30) NOT NULL,
    reference TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# index domin saurin transaction history
wallet_cur.execute("""
CREATE INDEX IF NOT EXISTS idx_wallet_transactions_user
ON wallet_transactions(user_id)
""")

# -------- WALLET DEPOSITS (PAYSTACK) --------
wallet_cur.execute("""
CREATE TABLE IF NOT EXISTS wallet_deposits (
    id TEXT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    amount BIGINT NOT NULL,
    type VARCHAR(30) DEFAULT 'wallet',
    paystack_ref TEXT UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP
)
""")

# index domin saurin lookup
wallet_cur.execute("""
CREATE INDEX IF NOT EXISTS idx_wallet_deposits_user
ON wallet_deposits(user_id)
""")

# -------- WALLET WITHDRAWALS (ADMIN USE) --------
wallet_cur.execute("""
CREATE TABLE IF NOT EXISTS wallet_withdrawals (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    amount BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    processed_by BIGINT,
    reference TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
)
""")

# index domin saurin admin queries
wallet_cur.execute("""
CREATE INDEX IF NOT EXISTS idx_wallet_withdrawals_user
ON wallet_withdrawals(user_id)
""")

#===============
# END DB MyWallet
#===============



# =========================
# DATABASE TABLES (SAFE)
# =========================


# ================= ADMIN NOTES TABLE =================

cur.execute("""
CREATE TABLE IF NOT EXISTS admin_notes (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ===== INDEX domin saurin fetch =====
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_admin_notes_admin
ON admin_notes(admin_id)
""")


# -------- MOVIES --------
cur.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id SERIAL PRIMARY KEY,
    title TEXT,
    price INTEGER,
    file_id TEXT,
    file_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel_msg_id INTEGER,
    channel_username TEXT
)
""")

# -------- ITEMS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    title TEXT,
    price INTEGER,
    file_id TEXT,
    file_name TEXT,
    group_key TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel_msg_id INTEGER,
    channel_username TEXT
)
""")

# -------- ORDERS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id BIGINT,
    movie_id INTEGER,
    item_id INTEGER,
    amount INTEGER,
    paid INTEGER DEFAULT 0,
    pay_ref TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(20) DEFAULT 'film'
)
""")


# -------- VIP MEMBERS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS vip_members (
    id SERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE NOT NULL,
    order_id TEXT,
    join_date TIMESTAMP,
    expire_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    warn1_sent BOOLEAN DEFAULT FALSE,
    warn2_sent BOOLEAN DEFAULT FALSE,
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    invite_link TEXT DEFAULT NULL
)
""")

# -------- ORDER ITEMS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id TEXT,
    movie_id INTEGER,
    item_id INTEGER,
    price INTEGER,
    file_id TEXT
)
""")

# -------- WEEKLY --------
cur.execute("""
CREATE TABLE IF NOT EXISTS weekly (
    id SERIAL PRIMARY KEY,
    poster_file_id TEXT,
    items TEXT,
    file_name TEXT,
    file_id TEXT,
    channel_msg_id INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------- CART --------
cur.execute("""
CREATE TABLE IF NOT EXISTS cart (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    movie_id INTEGER,
    item_id INTEGER,
    price INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------- REFERRALS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT,
    referred_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reward_granted INTEGER DEFAULT 0
)
""")

# -------- REORDERS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS reorders (
    old_order_id INTEGER,
    new_order_id INTEGER,
    user_id BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (old_order_id, user_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS referral_credits (
    id SERIAL PRIMARY KEY,
    referrer_id BIGINT,
    amount INTEGER,
    used INTEGER DEFAULT 0,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------- USER PREFS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS user_prefs (
    user_id BIGINT PRIMARY KEY,
    lang TEXT DEFAULT 'ha'
)
""")

# -------- USER LIBRARY --------
cur.execute("""
CREATE TABLE IF NOT EXISTS user_library (
    user_id BIGINT NOT NULL,
    movie_id INTEGER,
    item_id INTEGER,
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, movie_id, item_id)
)
""")

# -------- BUY ALL TOKENS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS buyall_tokens (
    token TEXT PRIMARY KEY,
    ids TEXT
)
""")

# -------- USER MOVIES --------
cur.execute("""
CREATE TABLE IF NOT EXISTS user_movies (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    movie_id INTEGER,
    item_id INTEGER,
    order_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resend_count INTEGER DEFAULT 0
)
""")

# =====================
# SERIES
# =====================
cur.execute("""
CREATE TABLE IF NOT EXISTS series (
    id SERIAL PRIMARY KEY,
    title TEXT,
    file_name TEXT,
    file_id TEXT,
    price INTEGER,
    poster_file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    channel_msg_id INTEGER,
    channel_username TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS series_items (
    id SERIAL PRIMARY KEY,
    series_id INTEGER,
    movie_id INTEGER,
    item_id INTEGER,
    file_id TEXT,
    title TEXT,
    order_id TEXT,
    price INTEGER DEFAULT 0,
    channel_msg_id INTEGER,
    channel_username TEXT,
    file_name TEXT
)
""")

# =====================
# FEEDBACK
# =====================
cur.execute("""
CREATE TABLE IF NOT EXISTS feedbacks (
    id SERIAL PRIMARY KEY,
    order_id TEXT NOT NULL UNIQUE,
    user_id BIGINT NOT NULL,
    mood TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS resend_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT,
    used_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# =====================
# HAUSA SERIES
# =====================
cur.execute("""
CREATE TABLE IF NOT EXISTS hausa_series (
    id SERIAL PRIMARY KEY,
    title TEXT,
    file_name TEXT,
    file_id TEXT,
    price INTEGER,
    series_id TEXT,
    poster_file_id TEXT,
    channel_msg_id INTEGER,
    channel_username TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS hausa_series_items (
    id SERIAL PRIMARY KEY,
    hausa_series_id INTEGER,
    movie_id INTEGER,
    item_id INTEGER,
    price INTEGER,
    file_id TEXT,
    title TEXT,
    order_id TEXT,
    series_id INTEGER,
    channel_msg_id INTEGER,
    channel_username TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_name TEXT
)
""")

# ================= VISITED USERS =================
cur.execute("""
CREATE TABLE IF NOT EXISTS visited_users (
    user_id BIGINT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# -------- ADMIN CONTROLS --------
cur.execute("""
CREATE TABLE IF NOT EXISTS admin_controls (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT UNIQUE,
    sendmovie_enabled INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# ================= HOW TO BUY =================
cur.execute("""
CREATE TABLE IF NOT EXISTS how_to_buy (
    id SERIAL PRIMARY KEY,
    hausa_text TEXT,
    english_text TEXT,
    media_file_id TEXT,
    media_type TEXT,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

print("✅ DATABASE READY — BIGINT FIX APPLIED")
import uuid
import re
import json
import requests
import traceback
import random
import difflib
from datetime import datetime, timedelta
import urllib.parse
import os
import hmac
import hashlib
# Store order message temporarily in memory
ORDER_MESSAGES = {}
admin_states = {}
active_links = {}
# --- Admins configuration ---
ADMINS = [8537505191]

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")

BOT_MODE = os.getenv("BOT_MODE", "polling")

CASHBACK = 20

VIP_PRICE = 1500
VIP_DURATION_VALUE = 33
VIP_DURATION_UNIT = "days"

WARNING_1_VALUE = 30
WARNING_1_UNIT = "days"

WARNING_2_VALUE = 32
WARNING_2_UNIT = "days"
ADMIN_ID = 8537505191
OTP_ADMIN_ID = 6603268127

BOT_USERNAME = "Algaitabot"
CHANNEL = "@Algaitamoviestore"

COUNTDOWN_SECONDS = 70
VIP_LINK = "https://t.me/+k4O-dsySLZBlOTM0"  # saka permanent group link naka
# ========= DATABASE CONFIG =========
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing")

# Flutterwave
FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY")
FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY")
FLW_WEBHOOK_SECRET = os.getenv("FLW_WEBHOOK_SECRET")
FLW_REDIRECT_URL = os.getenv("FLW_REDIRECT_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

FLW_BASE = "https://api.flutterwave.com/v3"



VIP_GROUP_ID = -1003656360408

# === PAYMENTS / STORAGE ===
PAYMENT_NOTIFY_GROUP = -1003555015230
STORAGE_CHANNEL = -1003520788779

PAYMENT_NOTIFY_GROUP_WALLET = -1003803657269

SEND_ADMIN_PAYMENT_NOTIF = False

ADMIN_USERNAME = "CEOalgaitabot"
#end

# ========= IMPORTS =========
import telebot
import hmac
import hashlib
import requests
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


# ========= BOT =========
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# ========= FLASK =========
app = Flask(__name__)


import time
import requests

def create_flutterwave_payment(user_id, order_id, amount, title):
    # ================= HEADERS =================
    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    # ================= PAYLOAD (FLUTTERWAVE FORMAT) =================
    payload = {
        "tx_ref": f"{order_id}_{int(time.time())}",  # ✅ Kamar yadda muka yi a baya
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": FLW_REDIRECT_URL,
        "payment_options": "card,ussd,banktransfer",
        "customer": {
            "email": f"user{user_id}@telegram.com",
            "name": f"User {user_id}"
        },
        "customizations": {
            "title": "Payment for " + title[:40],
            "description": f"Order ID: {order_id}"
        },
        "meta": {
            "order_id": str(order_id),
            "user_id": user_id,
            "title": title[:50]
        }
    }

    # ================= REQUEST =================
    try:
        r = requests.post(
            "https://api.flutterwave.com/v3/payments",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        data = r.json()
        
        # Duba idan komai yayi nasara
        if data.get("status") != "success":
            print(f"Flutterwave Error: {data.get('message')}")
            return None

        # Flutterwave tana dawo da link din a 'data' -> 'link'
        return data["data"]["link"]
        
    except Exception as e:
        print(f"Request Error: {e}")
        return None




# ========= HOME / KEEP ALIVE =========
@app.route("/")
def home():
    return "OK", 200


# ========= FLUTTERWAVE CALLBACK PAGE =========
@app.route("/flutterwave-callback", methods=["GET"])
def flutterwave_callback():
    return """
    <html>
    <head>
        <title>Payment Successful</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="5;url=https://t.me/Aslamtv2bot">
        <style>
            body {
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background-color: #f4f7f6;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .card {
                background: white;
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                text-align: center;
                width: 90%;
                max-width: 400px;
            }
            .icon {
                font-size: 70px;
                color: #2ecc71;
                margin-bottom: 20px;
            }
            h2 {
                color: #2c3e50;
                margin-bottom: 10px;
            }
            p {
                color: #7f8c8d;
                font-size: 18px;
                line-height: 1.6;
            }
            .btn {
                display: inline-block;
                margin-top: 25px;
                padding: 12px 30px;
                background-color: #0088cc;
                color: white;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                transition: background 0.3s;
            }
            .btn:hover {
                background-color: #0077b5;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h2>BIYA YA NASARA</h2>
            <p>An tabbatar da biyan ka cikin nasara.</p>
            <p>Zaka iya rufe browser ka koma Telegram yanzu.</p>
            <a href="https://t.me/Algaitabot" class="btn">KOMawa TELEGRAM</a>
        </div>
    </body>
    </html>
    """

# ========= FEEDBACK =========
def send_feedback_prompt(user_id, order_id):
    try:
        conn = get_conn()          # ✅ ABIN DA YA RASA
        cur = conn.cursor()

        cur.execute(
            "SELECT 1 FROM feedbacks WHERE order_id = %s",
            (order_id,)
        )
        exists = cur.fetchone()

        cur.close()
        conn.close()

    except Exception as e:
        print("FEEDBACK DB ERROR:", e)
        try:
            cur.close()
            conn.close()
        except:
            pass
        return  # DB ta kasa tashi → kar bot ya mutu

    if exists:
        return

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("😁 Very good", callback_data=f"feedback:very:{order_id}"),
        InlineKeyboardButton("🙂 Good", callback_data=f"feedback:good:{order_id}")
    )
    kb.add(
        InlineKeyboardButton("😓 Not sure", callback_data=f"feedback:neutral:{order_id}"),
        InlineKeyboardButton("😠 Angry", callback_data=f"feedback:angry:{order_id}")
    )

    try:
        bot.send_message(
            user_id,
            "We hope you enjoyed your shopping 🥰\nPlease choose how you’re feeling right now👇👇.",
            reply_markup=kb
        )
        print("✅ Feedback prompt sent:", user_id, order_id)
    except Exception as e:
        print("FEEDBACK SEND ERROR:", e)


@app.route("/webhook", methods=["POST"])
def flutterwave_webhook():
    try:
        # ================= SECURITY & VALIDATION (FLUTTERWAVE) =================
        signature = request.headers.get("verif-hash")
        if not signature: 
            return "Missing signature", 401
        
        if signature != FLW_WEBHOOK_SECRET: 
            return "Invalid signature", 401

        # ================= PAYLOAD =================
        payload = request.json or {}
        data = payload.get("data", {})
        
        status = (data.get("status") or "").lower()
        if status not in ("successful", "success"): 
            return "Ignored", 200

        raw_reference = data.get("tx_ref")
        currency = data.get("currency")
        
        # Safe amount conversion
        try:
            paid_amount = int(float(data.get("amount", 0)))
        except:
            paid_amount = 0

        # ✅ FIX REFERENCE: Ciro order_id ta hanyar split (kamar yadda aka gyara maka)
        order_id = raw_reference.split("_")[0] if raw_reference else None

        if not order_id:
            return "Order ID missing", 200

        # ================= DB =================
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT user_id, amount, paid, type
            FROM orders
            WHERE id=%s
            """,
            (order_id,)
        )
        row = cur.fetchone()

        if row:
            user_id, expected_amount, paid, order_type = row
        else:
            order_type = None

        # =====================================================
        # ================= WALLET TOPUP ======================
        # =====================================================

        if not row:
            wallet_conn = get_wallet_conn()
            wallet_cur = wallet_conn.cursor()

            wallet_cur.execute(
                """
                SELECT user_id, amount, status
                FROM wallet_deposits
                WHERE id=%s
                """,
                (order_id,)
            )

            dep = wallet_cur.fetchone()

            if not dep:
                wallet_cur.close()
                wallet_conn.close()
                cur.close()
                conn.close()
                return "Order not found", 200

            user_id, expected_amount, status = dep

            if status == "success":
                wallet_cur.close()
                wallet_conn.close()
                cur.close()
                conn.close()
                return "Already processed", 200

            # ✅ GYARA: Maimakon != expected_amount, mun yi amfani da < domin amincewa da biya
            if paid_amount < expected_amount or currency != "NGN":
                wallet_cur.close()
                wallet_conn.close()
                cur.close()
                conn.close()
                return "Wrong payment", 200

            wallet_cur.execute(
                """
                UPDATE wallet_deposits
                SET status='success',
                    paystack_ref=%s,
                    paid_at=NOW()
                WHERE id=%s
                """,
                (raw_reference, order_id)
            )

            wallet_cur.execute(
                """
                INSERT INTO wallet_balance (user_id, balance)
                VALUES (%s,%s)
                ON CONFLICT (user_id)
                DO UPDATE SET
                balance = wallet_balance.balance + EXCLUDED.balance,
                updated_at = NOW()
                """,
                (user_id, paid_amount)
            )

            wallet_cur.execute(
                """
                INSERT INTO wallet_transactions
                (user_id, amount, type, reference, description)
                VALUES (%s,%s,'deposit',%s,'Wallet Top-up')
                """,
                (user_id, paid_amount, order_id)
            )

            wallet_conn.commit()
            wallet_cur.close()
            wallet_conn.close()

            # ================= DELETE ORIGINAL ORDER MESSAGE =================
            if order_id in ORDER_MESSAGES:
                chat_id, message_id = ORDER_MESSAGES[order_id]
                try:
                    bot.delete_message(chat_id, message_id)
                except:
                    pass
                del ORDER_MESSAGES[order_id]

            # ================= USER INFO =================
            cur.execute(
                """
                SELECT first_name, last_name
                FROM visited_users
                WHERE user_id=%s
                """,
                (user_id,)
            )
            u = cur.fetchone()

            if u and (u[0] or u[1]):
                full_name = f"{u[0] or ''} {u[1] or ''}".strip()
            else:
                try:
                    chat = bot.get_chat(user_id)
                    full_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
                except:
                    full_name = "User"

            try:
                chat = bot.get_chat(user_id)
                tg_username = f"@{chat.username}" if chat.username else "unknown"
            except:
                tg_username = "unknown"

            wallet_kb = InlineKeyboardMarkup()
            wallet_kb.add(
                InlineKeyboardButton(
                    "🏦MY WALLET💵",
                    callback_data="wallet"
                )
            )

            bot.send_message(
                user_id,
                f"""🎉 <b>CONGRATULATIONS MALAM {full_name}</b>

💰 <b>Your wallet credited:</b> ₦{paid_amount}

🗃 <b>Order ID:</b> <code>{order_id}</code>

Your deposit was successful.

Use the button below to open your wallet.
""",
                parse_mode="HTML",
                reply_markup=wallet_kb
            )

            if PAYMENT_NOTIFY_GROUP:
                from datetime import datetime, timedelta
                now = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

                bot.send_message(
                    PAYMENT_NOTIFY_GROUP,
                    f"""💰 <b>TOP-UP SUCCESSFUL</b>

👤 <b>Name:</b> {full_name}
🔗 <b>Username:</b> {tg_username}
🆔 <b>User ID:</b> <code>{user_id}</code>

💳 <b>Top-up:</b> ₦{paid_amount}

🗃 <b>Order ID:</b> <code>{order_id}</code>
📊 <b>Status:</b> success

⏰ <b>Time:</b> {now}
""",
                    parse_mode="HTML"
                )

            cur.close()
            conn.close()
            return "OK", 200

        if paid == 1:
            cur.close()
            conn.close()
            return "Already processed", 200

        # ✅ GYARA: Maimakon != expected_amount, mun yi amfani da < domin amincewa da biya
        if paid_amount < expected_amount or currency != "NGN":
            cur.close()
            conn.close()
            return "Wrong payment", 200

        # ================= MARK AS PAID =================
        cur.execute(
            "UPDATE orders SET paid=1 WHERE id=%s",
            (order_id,)
        )

        # ================= DELETE ORIGINAL ORDER MESSAGE =================
        if order_id in ORDER_MESSAGES:
            chat_id, message_id = ORDER_MESSAGES[order_id]
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            del ORDER_MESSAGES[order_id]

        # ================= USER INFO =================
        cur.execute(
            """
            SELECT first_name, last_name
            FROM visited_users
            WHERE user_id=%s
            """,
            (user_id,)
        )
        u = cur.fetchone()

        if u and (u[0] or u[1]):
            full_name = f"{u[0] or ''} {u[1] or ''}".strip()
        else:
            try:
                chat = bot.get_chat(user_id)
                full_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            except:
                full_name = "User"

        try:
            chat = bot.get_chat(user_id)
            tg_username = f"@{chat.username}" if chat.username else "unknown"
        except:
            tg_username = "unknown"

        # =====================================================
        # ================== FILM ORDER =======================
        # =====================================================
        if order_type == "film":
            cur.execute(
                """
                SELECT i.title, i.group_key
                FROM order_items oi
                JOIN items i ON i.id = oi.item_id
                WHERE oi.order_id=%s
                """,
                (order_id,)
            )
            rows = cur.fetchall()

            if not rows:
                cur.close()
                conn.close()
                return "Empty order", 200

            groups = {}
            for title, group_key in rows:
                key = group_key or f"single_{title}"
                if key not in groups:
                    groups[key] = {"title": title, "count": 0}
                groups[key]["count"] += 1

            lines = []
            for g in groups.values():
                if g["count"] > 1:
                    lines.append(f"{g['title']} ({g['count']})")
                else:
                    lines.append(f"{g['title']}")

            titles_text = ", ".join(lines) if lines else "N/A"

            # ================= CASHBACK REWARD =================
            cashback = (paid_amount // 200) * CASHBACK
            if cashback > 200:
                cashback = 200

            if cashback > 0:
                wallet_conn = get_wallet_conn()
                wallet_cur = wallet_conn.cursor()

                wallet_cur.execute(
                    """
                    INSERT INTO wallet_balance (user_id, balance)
                    VALUES (%s,%s)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                    balance = wallet_balance.balance + EXCLUDED.balance,
                    updated_at = NOW()
                    """,
                    (user_id, cashback)
                )

                wallet_cur.execute(
                    """
                    INSERT INTO wallet_transactions
                    (user_id, amount, type, reference, description)
                    VALUES (%s,%s,'cashback',%s,'Movie Cashback Reward')
                    """,
                    (user_id, cashback, order_id)
                )

                wallet_conn.commit()
                wallet_cur.close()
                wallet_conn.close()

                bot.send_message(
                    user_id,
                    f"""🎁 Cashback Reward🎉

Wallet ID: <code>{user_id}</code>

You received ₦{cashback} cashback,  

Ka duba wallet din ka, zaka iya siyayya dashi a nan gaba.""" ,
                    parse_mode="HTML"
                )

            conn.commit()
            cur.close()
            conn.close()

            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "⬇️ DOWNLOAD NOW",
                    callback_data=f"deliver:{order_id}"
                )
            )

            bot.send_message(
                user_id,
                f"""🎉 <b>PAYMENT SUCCESSFUL</b>

👤 <b>Name:</b> {full_name}
🆔 <b>User ID:</b> <code>{user_id}</code>

🎬 <b>Items:</b> {titles_text}
🗃 <b>Order ID:</b> <code>{order_id}</code>

💳 <b>Amount Paid:</b> ₦{paid_amount}

⬇️ Click the button below to download your files.
""",
                parse_mode="HTML",
                reply_markup=kb
            )

            if PAYMENT_NOTIFY_GROUP:
                from datetime import datetime, timedelta
                now = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

                bot.send_message(
                    PAYMENT_NOTIFY_GROUP,
                    f"""✅ <b>NEW PAYMENT RECEIVED</b>

👤 <b>Name:</b> {full_name}
🔗 <b>Username:</b> {tg_username}
🆔 <b>User ID:</b> <code>{user_id}</code>

🎬 <b>Items:</b> {titles_text}
🗃 <b>Order ID:</b> <code>{order_id}</code>

💰 <b>Amount:</b> ₦{paid_amount}
⏰ <b>Time:</b> {now}
""",
                    parse_mode="HTML"
                )

            return "OK", 200

        # =====================================================
        # ================== VIP ORDER ========================
        # =====================================================
        elif order_type == "vip":
            from datetime import datetime, timedelta

            start_date = datetime.now()
            end_date = start_date + (
                timedelta(minutes=VIP_DURATION_VALUE)
                if VIP_DURATION_UNIT == "minutes"
                else timedelta(days=VIP_DURATION_VALUE)
            )

            start_local = start_date + timedelta(hours=1)
            end_local = end_date + timedelta(hours=1)

            already_in_group = False
            try:
                member = bot.get_chat_member(VIP_GROUP_ID, user_id)
                if member.status in ["member", "administrator", "creator"]:
                    already_in_group = True
            except:
                already_in_group = False

            if already_in_group:
                cur.execute(
                    """
                    INSERT INTO vip_members
                    (user_id, order_id, join_date, expire_at, status, warn1_sent, warn2_sent, payment_date)
                    VALUES (%s,%s,%s,%s,'active',FALSE,FALSE,NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        order_id = EXCLUDED.order_id,
                        join_date = EXCLUDED.join_date,
                        expire_at = EXCLUDED.expire_at,
                        status = 'active',
                        warn1_sent = FALSE,
                        warn2_sent = FALSE,
                        payment_date = NOW()
                    """,
                    (user_id, order_id, start_date, end_date)
                )

                conn.commit()
                cur.close()
                conn.close()

                bot.send_message(
                    user_id,
                    f"""💎 <b>AN SABUNTA VIP NAKA</b>

Muna tayaka murnar sabunta biyan VIP ɗinka.

Domin more samun duk fim ɗin da ranka yake so,
ci gaba da ziyartar VIP Group kawai.

📅 <b>Ka biya a yau:</b> {start_local.strftime("%Y-%m-%d")}
⏳ <b>Sake biya aranar ko kafin:</b> {end_local.strftime("%Y-%m-%d")}

Na gode da kasancewa tare da mu 🙏""",
                    parse_mode="HTML"
                )

                if PAYMENT_NOTIFY_GROUP:
                    now = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

                    bot.send_message(
                        PAYMENT_NOTIFY_GROUP,
                        f"""💎 <b>VIP RENEWAL PAYMENT</b>

👤 <b>Name:</b> {full_name}
🔗 <b>Username:</b> {tg_username}
🆔 <b>User ID:</b> <code>{user_id}</code>

🗃 <b>Order ID:</b> <code>{order_id}</code>

💰 <b>Amount:</b> ₦{paid_amount}
⏰ <b>Time:</b> {now}
""",
                        parse_mode="HTML"
                    )

                try:
                    bot.send_message(
                        ADMIN_ID,
                        f"🔔 VIP RENEWAL\n\n👤 {full_name}\n🆔 {user_id}\n💰 ₦{paid_amount}\n\nYa sabunta VIP dinsa."
                    )
                except:
                    pass

            else:
                cur.execute(
                    """
                    INSERT INTO vip_members
                    (user_id, order_id, join_date, expire_at, status, warn1_sent, warn2_sent, payment_date)
                    VALUES (%s,%s,NULL,NULL,'active',FALSE,FALSE,NOW())
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        order_id = EXCLUDED.order_id,
                        join_date = NULL,
                        expire_at = NULL,
                        status = 'active',
                        warn1_sent = FALSE,
                        warn2_sent = FALSE,
                        payment_date = NOW()
                    """,
                    (user_id, order_id)
                )

                conn.commit()
                cur.close()
                conn.close()

                vip_kb = InlineKeyboardMarkup()
                vip_kb.add(
                    InlineKeyboardButton(
                        "🔐 JOIN VIP GROUP",
                        callback_data=f"vipnow:{order_id}"
                    )
                )

                bot.send_message(
                    user_id,
                    f"""💎 <b>VIP SUBSCRIPTION ACTIVATED</b>

👤 <b>Name:</b> {full_name}
🆔 <b>User ID:</b> <code>{user_id}</code>

💳 <b>Amount Paid:</b> ₦{paid_amount}

📅 <b>Start Date:</b> {start_local.strftime("%Y-%m-%d")}
⏳ <b>End Date:</b> {end_local.strftime("%Y-%m-%d")}

🔐 Click the button below to join the VIP Group.
""",
                    parse_mode="HTML",
                    reply_markup=vip_kb
                )

                if PAYMENT_NOTIFY_GROUP:
                    now = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

                    bot.send_message(
                        PAYMENT_NOTIFY_GROUP,
                        f"""💎 <b>NEW VIP SUBSCRIPTION</b>

👤 <b>Name:</b> {full_name}
🔗 <b>Username:</b> {tg_username}
🆔 <b>User ID:</b> <code>{user_id}</code>

🗃 <b>Order ID:</b> <code>{order_id}</code>

💰 <b>Amount:</b> ₦{paid_amount}
⏰ <b>Time:</b> {now}
""",
                    parse_mode="HTML"
                )

            return "OK", 200

        return "OK", 200

    except Exception as e:
        print(f"Webhook Error: {e}")
        return "Internal Error", 500




# 
# ========= TELEGRAM WEBHOOK =========
@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200


import time
from telebot.apihelper import ApiTelegramException

@bot.callback_query_handler(func=lambda c: c.data.startswith("deliver:"))
def deliver_items(call):

    user_id = call.from_user.id

    try:
        _, order_id = call.data.split(":", 1)
    except:
        bot.answer_callback_query(call.id, "Invalid order information.")
        return

    conn = get_conn()
    cur = conn.cursor()

    # ================= CHECK ORDER =================
    cur.execute(
        "SELECT paid FROM orders WHERE id=%s AND user_id=%s",
        (order_id, user_id)
    )
    row = cur.fetchone()

    if not row or row[0] != 1:
        cur.close()
        conn.close()
        bot.answer_callback_query(
            call.id,
            "Your payment has not been confirmed yet."
        )
        return

    # ================= PREVENT RESEND =================
    cur.execute(
        "SELECT 1 FROM user_movies WHERE order_id=%s LIMIT 1",
        (order_id,)
    )
    if cur.fetchone():
        cur.close()
        conn.close()

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "PAID MOVIES",
                callback_data="my_movies"
            )
        )

        bot.send_message(
            user_id,
            "You have already received this movie.\n\n"
            "You can download it again from Paid Movies.",
            reply_markup=kb
        )
        return

    # remove popup message completely
    bot.answer_callback_query(call.id)

    # ================= FETCH ITEMS =================
    cur.execute(
        """
        SELECT oi.item_id, oi.file_id, i.title
        FROM order_items oi
        JOIN items i ON i.id = oi.item_id
        WHERE oi.order_id=%s
        """,
        (order_id,)
    )
    items = cur.fetchall()

    if not items:
        cur.close()
        conn.close()
        bot.send_message(user_id, "Order items not found.")
        return

    # ================= SAFE SEND FUNCTION =================
    def safe_send(chat_id, file_id, title):

        while True:
            try:
                try:
                    return bot.send_video(
                        chat_id,
                        file_id,
                        caption=f"{title}"
                    )
                except:
                    return bot.send_document(
                        chat_id,
                        file_id,
                        caption=f"{title}"
                    )

            except ApiTelegramException as e:

                if e.error_code == 429:
                    retry = int(e.result_json["parameters"]["retry_after"])

                    # ONLY visible message to user
                    bot.send_message(
                        chat_id,
                        "Wait...\n"
                        "Please wait, delivery will continue in a few seconds."
                    )

                    time.sleep(retry)
                    continue
                else:
                    return None

            except:
                return None

    # ================= SEND LOOP =================
    sent = 0

    for item_id, file_id, title in items:

        if not file_id:
            continue

        cur.execute(
            "SELECT 1 FROM user_movies WHERE user_id=%s AND item_id=%s",
            (user_id, item_id)
        )
        if cur.fetchone():
            continue

        msg = safe_send(user_id, file_id, title)

        if not msg:
            continue

        cur.execute(
            """
            INSERT INTO user_movies (user_id, item_id, order_id)
            VALUES (%s,%s,%s)
            """,
            (user_id, item_id, order_id)
        )

        sent += 1

        time.sleep(1.0)

    conn.commit()
    cur.close()
    conn.close()

    if sent == 0:
        bot.send_message(user_id, "Items could not be delivered.")
        return

    bot.send_message(
        user_id,
        f"Your movie(s) have been delivered ({sent}).\n"
        "Thank you for your purchase."
    )

    send_feedback_prompt(user_id, order_id)


# ================= ADMIN REMOVE MONEY FROM WALLET =================
@bot.message_handler(commands=["rage"])
def admin_remove_money(msg):

    user_id = msg.from_user.id

    # ===== ADMIN CHECK =====
    if user_id != ADMIN_ID:
        bot.reply_to(msg, "❌ You are not authorized to use this command.")
        return

    try:
        parts = msg.text.split()

        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /rage 500")
            return

        amount = int(parts[1])

        if amount <= 0:
            bot.reply_to(msg, "❌ Invalid amount.")
            return

    except:
        bot.reply_to(msg, "❌ Invalid format.\nUse: /rage 500")
        return

    # ===== DB =====
    wallet_conn = get_wallet_conn()
    wallet_cur = wallet_conn.cursor()

    try:

        # ===== CHECK CURRENT BALANCE =====
        wallet_cur.execute(
            "SELECT balance FROM wallet_balance WHERE user_id=%s",
            (user_id,)
        )
        row = wallet_cur.fetchone()

        current_balance = int(row[0]) if row else 0

        if current_balance < amount:
            bot.reply_to(
                msg,
                f"❌ Insufficient balance.\n\nYour Balance: ₦{current_balance}"
            )
            return

        # ===== DEDUCT BALANCE =====
        wallet_cur.execute(
            """
            UPDATE wallet_balance
            SET balance = balance - %s,
                updated_at = NOW()
            WHERE user_id=%s
            """,
            (amount, user_id)
        )

        # ===== SAVE TRANSACTION =====
        import time
        ref = f"debit_{user_id}_{int(time.time())}"

        wallet_cur.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, amount, type, reference, description)
            VALUES (%s,%s,'debit',%s,'Admin Wallet Debit')
            """,
            (user_id, amount, ref)
        )

        wallet_conn.commit()

        # ===== SUCCESS MESSAGE =====
        bot.reply_to(
            msg,
            f"""💸 <b>WALLET DEBIT SUCCESSFUL</b>

➖ Amount Removed: ₦{amount}
🆔 Wallet ID: <code>{user_id}</code>

Your wallet has been reduced successfully.""",
            parse_mode="HTML"
        )

    except:
        wallet_conn.rollback()
        bot.reply_to(msg, "❌ Failed to remove money.")

    finally:
        wallet_cur.close()
        wallet_conn.close()



# ================= CUSTOMER PAGINATION SYSTEM =================
CUSTOMER_CACHE = {}

@bot.message_handler(commands=["customers", "customershide"])
def customers_handler(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.text.lower()
    hide = msg.text.startswith("/customershide") or "hide" in text

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            o.user_id,
            SUM(o.amount) as total_paid,
            COUNT(o.id) as total_orders
        FROM orders o
        WHERE o.paid = 1
        GROUP BY o.user_id
        ORDER BY total_paid DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        bot.reply_to(msg, "❌ No customers found.")
        return

    CUSTOMER_CACHE[msg.from_user.id] = {
        "data": rows,
        "hide": hide
    }

    send_customer_page(msg.chat.id, msg.from_user.id, 0)


# ================= PAGE RENDER =================
def build_customer_text(admin_id, page):

    data = CUSTOMER_CACHE.get(admin_id)
    if not data:
        return None, None

    rows = data["data"]
    hide = data["hide"]

    per_page = 15
    total_pages = (len(rows) - 1) // per_page

    start = page * per_page
    end = start + per_page
    chunk = rows[start:end]

    conn = get_conn()
    cur = conn.cursor()

    result = []
    rank = start + 1

    for user_id, total_paid, total_orders in chunk:

        # ===== NAME =====
        cur.execute("""
            SELECT first_name, last_name
            FROM visited_users
            WHERE user_id=%s
        """, (user_id,))
        u = cur.fetchone()

        if u and (u[0] or u[1]):
            name = f"{u[0] or ''} {u[1] or ''}".strip()
        else:
            try:
                chat = bot.get_chat(user_id)
                name = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
            except:
                name = "Customer"

        # ===== PREFIX =====
        if rank <= 3:
            prefix = f"🏆{rank}"
        else:
            prefix = f"{rank}"

        # ===== FORMAT (SHORT AS YOU WANT) =====
        if hide:
            block = (
                f"{prefix}. 👤 {name}\n"
                f"📦 Orders: {total_orders}\n"
                f"🆔 Wallet ID: <code>{user_id}</code>"
            )
        else:
            block = (
                f"{prefix}. 👤 {name}\n"
                f"💰 ₦{int(total_paid)}\n"
                f"📦 Orders: {total_orders}\n"
                f"🆔 Wallet ID: <code>{user_id}</code>"
            )

        result.append(block)
        result.append("__________")

        rank += 1

    # remove last line
    if result and result[-1] == "__________":
        result.pop()

    cur.close()
    conn.close()

    text = "\n".join(result)

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("⬅️ Back", callback_data=f"custpage:{page-1}"),
        InlineKeyboardButton("➡️ Next", callback_data=f"custpage:{page+1}")
    )

    return text, kb


# ================= SEND FIRST =================
def send_customer_page(chat_id, admin_id, page):

    text, kb = build_customer_text(admin_id, page)

    if not text:
        return

    bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=kb
    )


# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: c.data.startswith("custpage:"))
def customer_pagination(c):

    if c.from_user.id != ADMIN_ID:
        return

    try:
        page = int(c.data.split(":")[1])
    except:
        return

    data = CUSTOMER_CACHE.get(c.from_user.id)
    if not data:
        return

    rows = data["data"]

    per_page = 15
    total_pages = (len(rows) - 1) // per_page

    # ===== POPUP ALERT =====
    if page < 0:
        bot.answer_callback_query(
            c.id,
            "🚫 Babu page a baya",
            show_alert=True
        )
        return

    if page > total_pages:
        bot.answer_callback_query(
            c.id,
            "🚫 Babu wani page a gaba",
            show_alert=True
        )
        return

    # ===== NORMAL EDIT =====
    bot.answer_callback_query(c.id)

    text, kb = build_customer_text(c.from_user.id, page)

    try:
        bot.edit_message_text(
            text,
            c.message.chat.id,
            c.message.message_id,
            parse_mode="HTML",
            reply_markup=kb
        )
    except:
        pass



# ================= ADMIN SALLAH GIFT =================
@bot.message_handler(commands=["sallah"])
def send_sallah_gift(msg):

    admin_id = msg.from_user.id

    if admin_id != ADMIN_ID:
        return

    try:
        parts = msg.text.replace("/sallah", "").strip().split(",")

        if len(parts) != 2:
            bot.reply_to(msg, "Usage: /sallah user_id, amount\nExample: /sallah 123456789, 300")
            return

        user_id = int(parts[0].strip())
        amount = int(parts[1].strip())

        if amount <= 0:
            bot.reply_to(msg, "❌ Invalid amount.")
            return

    except:
        bot.reply_to(msg, "❌ Invalid format.\nUse: /sallah 123456789, 300")
        return

    wallet_conn = get_wallet_conn()
    wallet_cur = wallet_conn.cursor()

    try:
        # ================= CHECK ADMIN BALANCE =================
        wallet_cur.execute(
            "SELECT balance FROM wallet_balance WHERE user_id=%s",
            (admin_id,)
        )
        row = wallet_cur.fetchone()

        admin_balance = int(row[0]) if row else 0

        if admin_balance < amount:
            bot.reply_to(msg, f"❌ Insufficient balance.\nYour Balance: ₦{admin_balance}")
            return

        # ================= GET USER ORDERS =================
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=%s AND paid=1",
            (user_id,)
        )
        order_row = cur.fetchone()
        total_orders = order_row[0] if order_row else 0

        cur.close()
        conn.close()

        # ================= DEDUCT ADMIN =================
        wallet_cur.execute(
            """
            UPDATE wallet_balance
            SET balance = balance - %s,
                updated_at = NOW()
            WHERE user_id=%s
            """,
            (amount, admin_id)
        )

        # ================= CREDIT USER =================
        wallet_cur.execute(
            """
            INSERT INTO wallet_balance (user_id, balance)
            VALUES (%s,%s)
            ON CONFLICT (user_id)
            DO UPDATE SET
            balance = wallet_balance.balance + EXCLUDED.balance,
            updated_at = NOW()
            """,
            (user_id, amount)
        )

        import time
        ref = f"sallah_{admin_id}_{int(time.time())}"

        # ================= SAVE TRANSACTION =================
        wallet_cur.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, amount, type, reference, description)
            VALUES (%s,%s,'sallah',%s,'Happy Sallah Gift')
            """,
            (user_id, amount, ref)
        )

        wallet_conn.commit()

        # ================= MESSAGE TO USER =================
        try:
            bot.send_message(
                user_id,
                f"""🌙✨ Barka da Sallah!

🎁 Wannan ita ce kyautarka daga Algaita Movie Store saboda goyon bayan da ka nuna wajen siyan fina-finai a wurinmu ❤️

💰 An saka maka kyauta a wallet ɗinka — gwargwadon yadda ka siya fim a wurinmu.
👉 Ka duba wallet ɗinka an tura maka kuɗinka.

📦 Your Orders: {total_orders}
💰 Kyautarka: ₦{amount}

Muna godiya sosai 🙏  
Za mu ci gaba da baka kyauta a duk lokacin da muka raba 🎬🔥

👉 Ka iya amfani da wannan kuɗin domin siyan fina-finai a bot ɗinmu.

🙏 Muna fatan duk lokacin da kake buƙatar wani fim, ba za ka manta da Algaita Movie Store ba.

— Algaita Movie Store  
🤖 @CEOalgaitabot"""
            )
        except:
            pass

        # ================= ADMIN CONFIRM =================
        bot.reply_to(
            msg,
            f"""✅ An turawa user

🆔 <code>{user_id}</code>
💰 ₦{amount}""",
            parse_mode="HTML"
        )

    except Exception:
        wallet_conn.rollback()
        bot.reply_to(msg, "❌ Failed to send gift.")

    finally:
        wallet_cur.close()
        wallet_conn.close()


# ================= EID BROADCAST SYSTEM =================
from telebot.apihelper import ApiTelegramException
import time

EID_MESSAGE = """🌙✨ Barka da Sallah!

Allah ya karɓi ibadunmu 🤲

Mun gode da goyon bayan ku ❤️

🎉 Ga wani albishir! A wannan Sallah ba za mu barku haka ba — dole sai mun faranta ran wasu daga cikin ku saboda yadda kuka dage da siyan fina-finai a gurinmu 🎬

🎁 Kyaututtuka na kuɗi za su shiga kai tsaye wallet ɗinku 💰 Yawan siyayyarka zai ƙayyade girman kyautarka 😉

— Algaita Movie Store  
CEO: Nazifi Ibrahim  
🤖 @CEOalgaitabot
"""


@bot.message_handler(commands=["sending"])
def send_eid_broadcast(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    bot.reply_to(msg, "⏳ Loading... Ana tura sakonni...")

    conn = get_conn()
    cur = conn.cursor()

    try:
        # ================= GET ALL USERS (PAID + UNPAID) =================
        cur.execute("""
            SELECT DISTINCT user_id FROM orders
        """)
        rows = cur.fetchall()

        users = [r[0] for r in rows]

    except:
        bot.send_message(msg.chat.id, "❌ Failed to fetch users.")
        return

    finally:
        cur.close()
        conn.close()

    if not users:
        bot.send_message(msg.chat.id, "❌ No users found.")
        return

    sent = 0
    failed = 0

    # ================= SAFE SEND FUNCTION =================
    def safe_send(user_id):

        while True:
            try:
                bot.send_message(user_id, EID_MESSAGE)
                return True

            except ApiTelegramException as e:

                # ===== RATE LIMIT =====
                if e.error_code == 429:
                    try:
                        retry = int(e.result_json["parameters"]["retry_after"])
                    except:
                        retry = 30

                    time.sleep(retry)
                    continue

                # ===== BLOCKED / FORBIDDEN =====
                elif e.error_code == 403:
                    return False

                else:
                    time.sleep(3)
                    return False

            except:
                time.sleep(3)
                return False

    # ================= LOOP =================
    for user_id in users:

        ok = safe_send(user_id)

        if ok:
            sent += 1
        else:
            failed += 1

        time.sleep(2)  # SAFE DELAY

    # ================= FINAL REPORT =================
    bot.send_message(
        msg.chat.id,
        f"""✅ BROADCAST COMPLETED

📤 Sent: {sent}
❌ Failed: {failed}
👥 Total: {len(users)}
"""
    )


# ================= ADMIN SAVE SYSTEM =================

# -------- SAVE --------
@bot.message_handler(commands=["save"])
def save_note(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    # REMOVE COMMAND ONLY (keep multi-line)
    text = msg.text.replace("/save", "", 1).strip()

    if not text:
        bot.reply_to(msg, "❌ Rubuta abin da zaka ajiye.")
        return

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO admin_notes (admin_id, content) VALUES (%s,%s)",
            (msg.from_user.id, text)
        )
        conn.commit()

        bot.reply_to(msg, "✅ An ajiye.")

    except:
        conn.rollback()
        bot.reply_to(msg, "❌ Failed.")

    finally:
        cur.close()
        conn.close()


# -------- VIEW ALL --------
@bot.message_handler(commands=["mysave"])
def view_notes(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT content FROM admin_notes WHERE admin_id=%s ORDER BY id DESC",
        (msg.from_user.id,)
    )
    rows = cur.fetchall()

    cur.close()
    conn.close()

    if not rows:
        bot.reply_to(msg, "📭 Babu komai a ajiya.")
        return

    result = []

    for (content,) in rows:
        result.append(content)

    final_text = "\n__________\n".join(result)

    bot.send_message(
        msg.chat.id,
        final_text
    )

# ================= USERS COUNTER SYSTEM =================
@bot.message_handler(commands=["users"])
def count_all_users(msg):

    if msg.from_user.id != ADMIN_ID:
        return

    conn = get_conn()
    cur = conn.cursor()

    try:
        # ===== COUNT ALL UNIQUE USERS (PAID + UNPAID) =====
        cur.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM orders
        """)
        total_users = cur.fetchone()[0] or 0

        # ===== COUNT PAID USERS =====
        cur.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM orders
            WHERE paid = 1
        """)
        paid_users = cur.fetchone()[0] or 0

        # ===== COUNT PENDING USERS =====
        cur.execute("""
            SELECT COUNT(DISTINCT user_id)
            FROM orders
            WHERE paid = 0
        """)
        pending_users = cur.fetchone()[0] or 0

        # ===== MESSAGE =====
        bot.send_message(
            msg.chat.id,
            f"""🎉 <b>OUR USERS</b>

👥 Total Users: <b>{total_users}</b>

✅ Paid Users: <b>{paid_users}</b>
⏳ Pending Users: <b>{pending_users}</b>
""",
            parse_mode="HTML"
        )

    except:
        bot.reply_to(msg, "❌ Failed to fetch users.")

    finally:
        cur.close()
        conn.close()



@bot.callback_query_handler(func=lambda c: c.data == "vipgroup")
def vip_group_info(call):

    text = """💎 <b>TSARIN SHIGA VIP GROUP</b>
━━━━━━━━━━━━━━━━━━
🔹 <b>Kudin Rijista:</b> ₦1,500  
🔹 <b>Subscription:</b> Kwana 33  
🔹 Ba za a sake biyan kudi ba har sai bayan kwanaki 30
━━━━━━━━━━━━━━━━━━
🔹 Bayan ka biya, za a tura maka <b>1-Time Secure Link</b>  
🔹 A cikin VIP ana saka <b>sabbin fina-finan India duk sati</b>
📅 <b>Ranaku:</b> Lahadi & Laraba
━━━━━━━━━━━━━━━━━━
🎬 Kana da damar neman:
• Sabon fim  
• Tsohon fim  
• Fim na musamman  
Ba tare da sake biyan wani ƙarin kuɗi ba.
━━━━━━━━━━━━━━━━━━
🔒 <b>VIP SUBSCRIPTION</b>
👇👇👇👇👇👇👇
"""

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("💳 SUBSCRIBE NOW", callback_data="subvip")
    )

    bot.send_message(
        call.message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

    bot.answer_callback_query(call.id)


# ================= ADMIN ADD MONEY TO WALLET =================
@bot.message_handler(commands=["addmoney"])
def admin_add_money(msg):

    user_id = msg.from_user.id

    # ===== ADMIN CHECK =====
    if user_id != ADMIN_ID:
        bot.reply_to(msg, "❌ You are not authorized to use this command.")
        return

    try:
        parts = msg.text.split()

        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /addmoney 500")
            return

        amount = int(parts[1])

        if amount <= 0:
            bot.reply_to(msg, "❌ Invalid amount.")
            return

    except:
        bot.reply_to(msg, "❌ Invalid format.\nUse: /addmoney 500")
        return

    # ===== DB =====
    wallet_conn = get_wallet_conn()
    wallet_cur = wallet_conn.cursor()

    try:

        # ===== UPDATE BALANCE =====
        wallet_cur.execute(
            """
            INSERT INTO wallet_balance (user_id, balance)
            VALUES (%s,%s)
            ON CONFLICT (user_id)
            DO UPDATE SET
            balance = wallet_balance.balance + EXCLUDED.balance,
            updated_at = NOW()
            """,
            (user_id, amount)
        )

        # ===== SAVE TRANSACTION =====
        ref = f"admin_{user_id}_{int(time.time())}"

        wallet_cur.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, amount, type, reference, description)
            VALUES (%s,%s,'admin_credit',%s,'Admin Wallet Funding')
            """,
            (user_id, amount, ref)
        )

        wallet_conn.commit()

        # ===== SUCCESS MESSAGE =====
        bot.reply_to(
            msg,
            f"""✅ <b>WALLET FUNDED SUCCESSFULLY</b>

💰 Amount Added: ₦{amount}
🆔 Wallet ID: <code>{user_id}</code>

Your wallet has been credited successfully.""",
            parse_mode="HTML"
        )

    except Exception as e:
        wallet_conn.rollback()
        bot.reply_to(msg, "❌ Failed to add money.")
    
    finally:
        wallet_cur.close()
        wallet_conn.close()


# ======= VIP ORDER CREATOR (CALLBACK subvip) =========
import uuid
from psycopg2.extras import RealDictCursor

@bot.callback_query_handler(func=lambda c: c.data == "subvip")
def vipgroup_handler(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id
    first_name = c.from_user.first_name or "User"

    conn = get_conn()
    if not conn:
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ========= CHECK EXISTING UNPAID VIP =========
    cur.execute(
        """
        SELECT id, amount
        FROM orders
        WHERE user_id=%s
          AND type='vip'
          AND paid=0
        LIMIT 1
        """,
        (uid,)
    )
    row = cur.fetchone()

    # ========= REUSE OR CREATE =========
    if row:
        order_id = row["id"]

        if int(row["amount"]) != int(VIP_PRICE):
            cur.execute(
                "UPDATE orders SET amount=%s WHERE id=%s",
                (VIP_PRICE, order_id)
            )
            conn.commit()
    else:
        order_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO orders (id, user_id, amount, paid, type)
            VALUES (%s,%s,%s,0,'vip')
            """,
            (order_id, uid, VIP_PRICE)
        )
        conn.commit()

    # ========= CREATE PAYMENT LINK (Flutterwave) =========
    # Mun sauya daga create_paystack_payment zuwa create_flutterwave_payment
    pay_url = create_flutterwave_payment(
        uid,
        order_id,
        VIP_PRICE,
        "VIP Subscription"
    )

    if not pay_url:
        bot.send_message(uid, "❌ Sorry, payment gateway is down. Try again later.")
        cur.close()
        conn.close()
        return

    # ========= FORMAT =========
    if VIP_DURATION_UNIT == "minutes":
        duration_text = f"{VIP_DURATION_VALUE} Minutes"
    else:
        duration_text = f"{VIP_DURATION_VALUE} Days"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"💳 Pay ₦{VIP_PRICE}", url=pay_url))
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}"))

    # ✅ EDIT MESSAGE INSTEAD OF SEND
    bot.edit_message_text(
        f"""🔥 <b>UNLOCK VIP ACCESS</b> 🔥

{first_name}, you are almost in our VIP group.

💎 VIP Algaita Bot(Group)
💵 ₦{VIP_PRICE} only
⏳ {duration_text} access

⚡ Access starts after payment
🔐 Secure payment

Tap below to continue👇.
""",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        parse_mode="HTML",
        reply_markup=kb
    )

    # ✅ STORE MESSAGE IN MEMORY
    ORDER_MESSAGES[order_id] = (
        c.message.chat.id,
        c.message.message_id
    )

    cur.close()
    conn.close()




import threading  
import time  
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton  
  
  
@bot.callback_query_handler(func=lambda c: c.data.startswith("vipnow:"))  
def handle_vip_join(c):  
  
    try:  
        bot.answer_callback_query(c.id)  
  
        user_id = c.from_user.id  
        first_name = c.from_user.first_name or "User"  
  
        sent_chat_id = c.message.chat.id  
        sent_message_id = c.message.message_id  
  
        # ===== JOIN BUTTON =====  
        kb = InlineKeyboardMarkup()  
        kb.add(  
            InlineKeyboardButton(  
                "🔐 Join VIP Now",  
                url=VIP_LINK  
            )  
        )  
  
        bot.edit_message_text(  
            f"🔐 <b>VIP ACCESS READY</b>\n\n"  
            f"⏳ Link expires in {COUNTDOWN_SECONDS} seconds...\n\n"  
            f"Tap below to join 👇",  
            chat_id=sent_chat_id,  
            message_id=sent_message_id,  
            parse_mode="HTML",  
            reply_markup=kb  
        )  
  
        # ===== COUNTDOWN =====  
        def countdown():  
  
            for remaining in range(COUNTDOWN_SECONDS - 1, -1, -1):  
  
                time.sleep(1)  
  
                # ===== CHECK DIRECT FROM GROUP =====  
                try:  
                    member = bot.get_chat_member(VIP_GROUP_ID, user_id)  
  
                    if member.status in ["member", "administrator", "creator"]:  
  
                        # ================= DB UPDATE ACTIVE =================  
                        try:  
                            from datetime import datetime, timedelta  
  
                            conn = get_conn()  
                            cur = conn.cursor()  
  
                            # ✅ JOIN DATE = lokacin da ya shiga  
                            join_date = datetime.now()  
  
                            # ✅ EXPIRE = lissafi daga saman file  
                            if VIP_DURATION_UNIT == "minutes":  
                                expire_at = join_date + timedelta(minutes=VIP_DURATION_VALUE)  
                            else:  
                                expire_at = join_date + timedelta(days=VIP_DURATION_VALUE)  
  
                            # ===== CHECK IF USER EXISTS =====
                            cur.execute(
                                "SELECT 1 FROM vip_members WHERE user_id=%s",
                                (user_id,)
                            )
                            exists = cur.fetchone()

                            if exists:
                                cur.execute(  
                                    """  
                                    UPDATE vip_members  
                                    SET status='active',  
                                        join_date=%s,  
                                        expire_at=%s,  
                                        warn1_sent=FALSE,  
                                        warn2_sent=FALSE  
                                    WHERE user_id=%s  
                                    """,  
                                    (join_date, expire_at, user_id)  
                                )  
                            else:
                                cur.execute(
                                    """
                                    INSERT INTO vip_members
                                    (user_id, status, join_date, expire_at, warn1_sent, warn2_sent)
                                    VALUES (%s, 'active', %s, %s, FALSE, FALSE)
                                    """,
                                    (user_id, join_date, expire_at)
                                )

                            conn.commit()  
                            cur.close()  
                            conn.close()  
  
                        except:  
                            pass  
                        # =====================================================  
  
                        # EDIT MESSAGE TO USER JOINED  
                        try:  
                            bot.edit_message_text(  
                                f"{first_name} Joined ✅",  
                                chat_id=sent_chat_id,  
                                message_id=sent_message_id  
                            )  
                        except:  
                            pass  
  
                        # SEND THANK YOU PRIVATE MESSAGE  
                        try:  
                            bot.send_message(  
                                user_id,  
                                "🙏 Thank you our valued customer.\n"  
                                "Fatanmu zakaji dadin wannan group."  
                            )  
                        except:  
                            pass  
  
                        return  
                except:  
                    pass  
  
                # ===== UPDATE COUNTDOWN =====  
                try:  
                    bot.edit_message_text(  
                        f"🔐 <b>VIP ACCESS READY</b>\n\n"  
                        f"⏳ Link expires in {remaining} seconds...\n\n"  
                        f"Tap below to join 👇",  
                        chat_id=sent_chat_id,  
                        message_id=sent_message_id,  
                        parse_mode="HTML",  
                        reply_markup=kb  
                    )  
                except:  
                    pass  
  
            # ===== TIME OUT =====  
            admin_kb = InlineKeyboardMarkup()  
            admin_kb.add(  
                InlineKeyboardButton(  
                    "👤ADMIN HELP",  
                    url=f"https://t.me/{ADMIN_USERNAME}"  
                )  
            )  
  
            try:  
                bot.edit_message_text(  
                    "❌ TIME OUT\n\n"  
                    "This link has expired.",  
                    chat_id=sent_chat_id,  
                    message_id=sent_message_id,  
                    reply_markup=admin_kb  
                )  
            except:  
                pass  
  
            try:  
                time.sleep(2)  
                bot.send_message(  
                    user_id,  
                    "An turama maka link amma link din har yayi expire\n"  
                    "baka shiga ba don haka tintini admin."  
                )  
            except:  
                pass  
  
        threading.Thread(target=countdown).start()  
  
    except:  
        pass  
  
import threading  
import time  
from datetime import datetime  
  
def vip_expiry_checker():  
  
    while True:  
        try:  
            conn = get_conn()  
            cur = conn.cursor()  
  
            cur.execute(  
                """  
                SELECT user_id  
                FROM vip_members  
                WHERE status='active'  
                AND expire_at IS NOT NULL  
                AND expire_at <= NOW()  
                """  
            )  
  
            expired_users = cur.fetchall()  
  
            for row in expired_users:  
                user_id = row[0]  
  
                # ===== REMOVE FROM GROUP (NOT PERMANENT BAN) =====  
                try:  
                    bot.ban_chat_member(VIP_GROUP_ID, user_id)  
                    bot.unban_chat_member(VIP_GROUP_ID, user_id)  
                except:  
                    pass  
  
                # ===== UPDATE STATUS =====  
                try:  
                    cur.execute(  
                        """  
                        UPDATE vip_members  
                        SET status='expired'  
                        WHERE user_id=%s  
                        """,  
                        (user_id,)  
                    )  
                    conn.commit()  
  
                    # ===== WARNING 3 CALL =====  
                    send_expired_message(user_id)  
  
                except:  
                    pass  
  
            cur.close()  
            conn.close()  
  
        except:  
            pass  
  
        time.sleep(43200)  # check every 60 seconds  
  
  
threading.Thread(target=vip_expiry_checker, daemon=True).start()

# ==========================================
# VIP WARNING SYSTEM (HAUSA VERSION)
# ==========================================

import threading
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def vip_warning_system():

    while True:
        try:
            conn = get_conn()
            cur = conn.cursor()

            now = datetime.now()

            # ===============================
            # GET ALL ACTIVE USERS
            # ===============================
            cur.execute("""
                SELECT user_id, expire_at, warn1_sent, warn2_sent
                FROM vip_members
                WHERE status='active'
                AND expire_at IS NOT NULL
            """)

            users = cur.fetchall()

            for user_id, expire_at, warn1_sent, warn2_sent in users:

                if not expire_at:
                    continue

                remaining = expire_at - now
                remaining_seconds = remaining.total_seconds()

                if remaining_seconds <= 0:
                    continue

                # =================================
                # CONVERT WARNING 1 THRESHOLD
                # =================================
                if WARNING_1_UNIT == "minutes":
                    threshold1 = timedelta(minutes=WARNING_1_VALUE)
                    time_left_value = int(remaining_seconds // 60)
                    unit_text = "minti"
                else:
                    threshold1 = timedelta(days=WARNING_1_VALUE)
                    time_left_value = remaining.days
                    unit_text = "kwana"

                # =================================
                # WARNING 1
                # =================================
                if not warn1_sent and remaining <= threshold1:

                    try:
                        kb = InlineKeyboardMarkup()
                        kb.add(
                            InlineKeyboardButton(
                                "💳REPAY NOW",
                                callback_data="subvip"
                            )
                        )

                        bot.send_message(
                            user_id,
                            f"⏳ TUNATARWA ZANYI MAKA\n\n"
                            f"Subscription ɗinka (ALGAITA VIP) zai kare nan da {time_left_value} {unit_text}.\n\n"
                            f"Muna matuƙar godiya da kasancewarka tare da mu ❤️\n"
                            f"Da fatan za ka sabunta kafin lokacin ya ƙare domin cigaba da more VIP group.",
                            reply_markup=kb
                        )

                        cur.execute("""
                            UPDATE vip_members
                            SET warn1_sent=TRUE
                            WHERE user_id=%s
                        """, (user_id,))
                        conn.commit()

                    except:
                        pass

                # =================================
                # CONVERT WARNING 2 THRESHOLD
                # =================================
                if WARNING_2_UNIT == "minutes":
                    threshold2 = timedelta(minutes=WARNING_2_VALUE)
                    time_left_value2 = int(remaining_seconds // 60)
                    unit_text2 = "minti"
                else:
                    threshold2 = timedelta(days=WARNING_2_VALUE)
                    time_left_value2 = remaining.days
                    unit_text2 = "kwana"

                # =================================
                # WARNING 2 (FINAL)
                # =================================
                if not warn2_sent and remaining <= threshold2:

                    try:
                        kb = InlineKeyboardMarkup()
                        kb.add(
                            InlineKeyboardButton(
                                "💳REPAY NOW",
                                callback_data="subvip"
                            )
                        )

                        bot.send_message(
                            user_id,
                            f"⚠NAZO NA SANAR DAKAI\n\n"
                            f"Subscription ɗinka (ALGAITA VIP) zai kare nan da {time_left_value2} {unit_text2}.\n\n"
                            f"Idan ba ka sabunta ba kafin lokacin ya cika, za a cire ka daga VIP group.\n"
                            f"Da fatan za ka sabunta yanzu domin kada a cire ka.",
                            reply_markup=kb
                        )

                        cur.execute("""
                            UPDATE vip_members
                            SET warn2_sent=TRUE
                            WHERE user_id=%s
                        """, (user_id,))
                        conn.commit()

                    except:
                        pass

            cur.close()
            conn.close()

        except:
            pass

        time.sleep(7200)  # yana duba duk 30 seconds


threading.Thread(target=vip_warning_system, daemon=True).start()



# ==========================================
# WARNING 3 (AFTER USER REMOVAL MESSAGE)
# SAKA WANNAN A CIKIN EXPIRY CHECKER
# BAYAN AN CANZA status='expired'
# ==========================================

def send_expired_message(user_id):
    try:
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "💳REPAY NOW",
                callback_data="subvip"
            )
        )

        bot.send_message(
            user_id,
            "❌ An Cire Ka Daga VIP\n\n"
            "An cire ka daga VIP group saboda subscription ɗinka ya ƙare.\n\n"
            "Idan kana son komawa domin cigaba da more manyan fina-finai sababbi da tsofaffi,\n"
            "za ka iya sabunta biyanka yanzu.",
            reply_markup=kb
        )
    except:
        pass



# ==========================================
# ADMIN MANUAL VIP ADD SYSTEM (/vip)
# ==========================================

from datetime import datetime, timedelta

vip_waiting_admin = set()


# ===============================
# /vip COMMAND (ADMIN ONLY)
# ===============================
@bot.message_handler(commands=['vip'])
def vip_command(message):

    if message.from_user.id != ADMIN_ID:
        return

    vip_waiting_admin.add(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "Turo min user ID ɗin wanda kake son saka a VIP."
    )


# ===============================
# RECEIVE USER ID
# ===============================
@bot.message_handler(func=lambda m: m.from_user.id in vip_waiting_admin)
def receive_vip_user_id(message):

    if message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = int(message.text.strip())
    except:
        bot.send_message(message.chat.id, "ID bai inganta ba. Tura lambar user ID kawai.")
        return

    vip_waiting_admin.remove(message.from_user.id)

    # ===============================
    # CHECK IF USER IS IN GROUP
    # ===============================
    try:
        member = bot.get_chat_member(VIP_GROUP_ID, user_id)

        if member.status not in ["member", "administrator", "creator"]:
            bot.send_message(
                message.chat.id,
                "Wannan user baya cikin group ɗin."
            )
            return

    except:
        bot.send_message(
            message.chat.id,
            "Wannan user baya cikin group ɗin."
        )
        return

    # ===============================
    # CREATE JOIN + EXPIRE DATE
    # ===============================
    join_date = datetime.now()

    if VIP_DURATION_UNIT == "minutes":
        expire_at = join_date + timedelta(minutes=VIP_DURATION_VALUE)
    else:
        expire_at = join_date + timedelta(days=VIP_DURATION_VALUE)

    # ===============================
    # INSERT OR UPDATE USER
    # ===============================
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO vip_members (user_id, join_date, expire_at, status, warn1_sent, warn2_sent)
            VALUES (%s, %s, %s, 'active', FALSE, FALSE)
            ON CONFLICT (user_id)
            DO UPDATE SET
                join_date = EXCLUDED.join_date,
                expire_at = EXCLUDED.expire_at,
                status = 'active',
                warn1_sent = FALSE,
                warn2_sent = FALSE
        """, (user_id, join_date, expire_at))

        conn.commit()
        cur.close()
        conn.close()

    except:
        bot.send_message(message.chat.id, "An samu matsala wajen saka user a DB.")
        return

    # ===============================
    # SUCCESS MESSAGE TO ADMIN
    # ===============================
    
    # ✅ DISPLAY FIX (Nigeria Time +1 hour)
    expire_local = expire_at + timedelta(hours=1)
    expire_text = expire_local.strftime("%d %B %Y %H:%M:%S")

    bot.send_message(
        message.chat.id,
        f"An saka user {user_id} a VIP.\n\n"
        f"Za a cire shi ranar:\n{expire_text}"
    )


# MY WALLET SYSTEM
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data == "wallet")
def open_wallet(c):

    # Kare error idan ba callback query ba
    try:
        bot.answer_callback_query(c.id)
    except:
        pass

    uid = c.from_user.id
    name = c.from_user.first_name or "User"

    conn = get_wallet_conn()
    if not conn:
        return

    cur = conn.cursor()

    # ===== CHECK WALLET =====
    cur.execute(
        "SELECT balance FROM wallet_balance WHERE user_id=%s",
        (uid,)
    )
    row = cur.fetchone()

    if row:
        balance = int(row[0])
        text = f"""Malam {name}
Ragowar kudin ka ya rage

💰 {name} Wallet
🆔 Wallet ID: <code>{uid}</code>

Balance: ₦{balance}
"""
    else:
        balance = 0
        text = f"""Malam {name}
Yi hakuri baka da kudi a wallet din ka

💰 {name} Wallet
🆔 Wallet ID: <code>{uid}</code>

Balance: ₦0
"""

    # ===== BUTTONS =====
    kb = InlineKeyboardMarkup()

    # Row 1
    kb.row(
        InlineKeyboardButton("➕ Add Money", callback_data="add_money"),
        InlineKeyboardButton("📜 Transactions", callback_data="wallet_history")
    )

    # Row 2
    kb.row(
        InlineKeyboardButton("💸 Transfer Money", callback_data="transfer_money")
    )

    # ===== SEND MESSAGE =====
    bot.send_message(
        uid,
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

    cur.close()
    conn.close()

# ==========================================
# ==========================================
# BACK TO WALLET (EDIT MESSAGE)
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data == "wallet_back")
def wallet_back(c):

    # 🔒 Kare error idan ba callback query ba
    try:
        bot.answer_callback_query(c.id)
    except:
        pass

    uid = c.from_user.id
    name = c.from_user.first_name or "User"

    conn = get_wallet_conn()
    if not conn:
        return

    cur = conn.cursor()

    cur.execute(
        "SELECT balance FROM wallet_balance WHERE user_id=%s",
        (uid,)
    )

    row = cur.fetchone()

    if row:
        balance = int(row[0])
        text = f"""Malam {name}
Ragowar kudin ka ya rage

💰 {name} Wallet
🆔 Wallet ID: <code>{uid}</code>

Balance: ₦{balance}
"""
    else:
        text = f"""Malam {name}
Yi hakuri baka da kudi a wallet din ka

💰 {name} Wallet
🆔 Wallet ID: <code>{uid}</code>

Balance: ₦0
"""

    kb = InlineKeyboardMarkup()

    kb.row(
        InlineKeyboardButton("➕ Add Money", callback_data="add_money"),
        InlineKeyboardButton("📜 Transactions", callback_data="wallet_history")
    )

    kb.row(
        InlineKeyboardButton("💸 Transfer Money", callback_data="transfer_money")
    )

    bot.edit_message_text(
        text,
        chat_id=uid,
        message_id=c.message.message_id,
        reply_markup=kb,
        parse_mode="HTML"
    )

    cur.close()
    conn.close()



# ==========================================
# WALLET LAST 5 TRANSACTIONS
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data == "wallet_history")
def wallet_history(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id

    conn = get_wallet_conn()
    if not conn:
        return

    cur = conn.cursor()

    # ===== GET LAST 5 =====
    cur.execute(
        """
        SELECT amount, type, description, created_at
        FROM wallet_transactions
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 5
        """,
        (uid,)
    )

    rows = cur.fetchall()

    if not rows:

        text = """📜 WALLET TRANSACTIONS

Babu wani transaction a wallet ɗinka tukuna."""

    else:

        # ===== FORMAT MESSAGE =====
        lines = []

        for amount, ttype, desc, time in rows:

            if ttype == "deposit":
                sign = "➕"
            elif ttype == "purchase":
                sign = "➖"
            else:
                sign = "•"

            lines.append(
                f"{sign} ₦{amount} — {desc}\n🕒 {time}"
            )

        text = "📜 LAST 5 WALLET TRANSACTIONS\n\n"
        text += "\n\n".join(lines)

    # ===== BUTTON =====
    kb = InlineKeyboardMarkup()

    kb.row(
        InlineKeyboardButton("⬅️ Back to Wallet", callback_data="wallet_back")
    )

    bot.edit_message_text(
        text,
        chat_id=uid,
        message_id=c.message.message_id,
        reply_markup=kb
    )

    cur.close()
    conn.close()

# ==========================================


@bot.callback_query_handler(func=lambda c: c.data == "add_money")
def add_money_menu(c):

    bot.answer_callback_query(c.id)

    text = """💰 *Add Money*

Zabi adadin da zaka deposit zuwa wallet din ka👇👇
"""

    kb = InlineKeyboardMarkup()

    kb.row(
        InlineKeyboardButton("₦200", callback_data="ng200"),
        InlineKeyboardButton("₦500", callback_data="ng500")
    )

    kb.row(
        InlineKeyboardButton("₦1000", callback_data="ng1000"),
        InlineKeyboardButton("₦1500", callback_data="ng1500")
    )

    kb.row(
        InlineKeyboardButton("₦2000", callback_data="ng2000")
    )

    bot.send_message(
        c.message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=kb
    )

import uuid
from psycopg2.extras import RealDictCursor

@bot.callback_query_handler(func=lambda c: c.data.startswith("ng"))
def wallet_amount_handler(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id
    name = c.from_user.first_name or "User"

    try:
        amount = int(c.data.replace("ng",""))
    except:
        return

    conn = get_wallet_conn()
    if not conn:
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ===== CHECK PENDING WALLET ORDER =====
    cur.execute(
        """
        SELECT id, amount
        FROM wallet_deposits
        WHERE user_id=%s
        AND status='pending'
        LIMIT 1
        """,
        (uid,)
    )

    row = cur.fetchone()

    # ===== REUSE ORDER =====
    if row:

        order_id = row["id"]

        if int(row["amount"]) != amount:

            cur.execute(
                """
                UPDATE wallet_deposits
                SET amount=%s
                WHERE id=%s
                """,
                (amount, order_id)
            )

            conn.commit()

    # ===== CREATE NEW ORDER =====
    else:

        order_id = str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO wallet_deposits
            (id, user_id, amount, type, status)
            VALUES (%s,%s,%s,'wallet','pending')
            """,
            (order_id, uid, amount)
        )

        conn.commit()

    cur.close()
    conn.close()

    # ===== CREATE PAYSTACK LINK =====
    pay_url = create_paystack_payment(
        uid,
        order_id,
        amount,
        "Wallet Top-up"
    )

    if not pay_url:
        return

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"💳 Top-up ₦{amount}", url=pay_url))
    kb.add(InlineKeyboardButton("❌ Cancel", callback_data="wallet_back"))

    bot.edit_message_text(
        f"""💰 *Wallet Deposit*

👤 Name: {name}

💳 Amount: ₦{amount}

🆔 Order ID:
`{order_id}`

Danna button da ke kasa domin biyan kudin.
""",
        chat_id=c.message.chat.id,
        message_id=c.message.message_id,
        parse_mode="Markdown",
        reply_markup=kb
    )

    # ===== STORE MESSAGE FOR WEBHOOK DELETE =====
    ORDER_MESSAGES[order_id] = (
        c.message.chat.id,
        c.message.message_id
    )



from datetime import datetime, timedelta

@bot.callback_query_handler(func=lambda c: c.data.startswith("walletpay:"))
def wallet_pay_handler(call):

    user_id = call.from_user.id

    try:
        _, order_id = call.data.split(":", 1)
    except:
        bot.answer_callback_query(call.id, "Invalid order.")
        return

    # ================= MAIN DB =================
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT user_id, amount, paid, type
        FROM orders
        WHERE id=%s
        """,
        (order_id,)
    )

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        bot.answer_callback_query(call.id, "Order not found.")
        return

    order_user, amount, paid, order_type = row

    if order_user != user_id:
        cur.close()
        conn.close()
        bot.answer_callback_query(call.id, "This order does not belong to you.")
        return

    if paid == 1:
        cur.close()
        conn.close()
        bot.answer_callback_query(call.id, "Order already paid.")
        return

    # ================= WALLET DB =================
    wallet_conn = get_wallet_conn()
    wallet_cur = wallet_conn.cursor()

    wallet_cur.execute(
        "SELECT balance FROM wallet_balance WHERE user_id=%s",
        (user_id,)
    )

    w = wallet_cur.fetchone()

    balance = int(w[0]) if w else 0

    # ================= INSUFFICIENT BALANCE =================
    if balance < amount:

        bot.answer_callback_query(
            call.id,
            f"❌ Insufficient wallet balance\n\n"
            f"Your balance: ₦{balance}\n"
            f"Movie price: ₦{amount}\n\n"
            f"Please click PAY NOW to complete payment.",
            show_alert=True
        )

        wallet_cur.close()
        wallet_conn.close()
        cur.close()
        conn.close()
        return

    # ================= DEDUCT WALLET =================
    wallet_cur.execute(
        """
        UPDATE wallet_balance
        SET balance = balance - %s,
            updated_at = NOW()
        WHERE user_id=%s
        """,
        (amount, user_id)
    )

    wallet_cur.execute(
        """
        INSERT INTO wallet_transactions
        (user_id, amount, type, reference, description)
        VALUES (%s,%s,'purchase',%s,'Movie Purchase')
        """,
        (user_id, amount, order_id)
    )

    wallet_conn.commit()

    wallet_cur.close()
    wallet_conn.close()

    # ================= MARK ORDER PAID =================
    cur.execute(
        "UPDATE orders SET paid=1 WHERE id=%s",
        (order_id,)
    )

    # ================= DELETE ORDER MESSAGE =================
    if order_id in ORDER_MESSAGES:

        chat_id, message_id = ORDER_MESSAGES[order_id]

        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass

        del ORDER_MESSAGES[order_id]

    # ================= USER INFO =================
    cur.execute(
        """
        SELECT first_name, last_name
        FROM visited_users
        WHERE user_id=%s
        """,
        (user_id,)
    )

    u = cur.fetchone()

    if u and (u[0] or u[1]):
        full_name = f"{u[0] or ''} {u[1] or ''}".strip()
    else:
        try:
            chat = bot.get_chat(user_id)
            full_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip()
        except:
            full_name = "User"

    try:
        chat = bot.get_chat(user_id)
        tg_username = f"@{chat.username}" if chat.username else "unknown"
    except:
        tg_username = "unknown"

    # ================= FETCH ITEMS =================
    cur.execute(
        """
        SELECT i.title, i.group_key
        FROM order_items oi
        JOIN items i ON i.id = oi.item_id
        WHERE oi.order_id=%s
        """,
        (order_id,)
    )

    rows = cur.fetchall()

    groups = {}

    for title, group_key in rows:

        key = group_key or f"single_{title}"

        if key not in groups:
            groups[key] = {"title": title, "count": 0}

        groups[key]["count"] += 1

    lines = []
    for g in groups.values():
        if g["count"] > 1:
            lines.append(f"{g['title']} ({g['count']})")
        else:
            lines.append(f"{g['title']}")

    titles_text = ", ".join(lines) if lines else "N/A"

    item_count = sum(g["count"] for g in groups.values())

    # ================= TIME =================
    now = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

    conn.commit()
    cur.close()
    conn.close()

    # ================= USER MESSAGE =================
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton(
            "⬇️ DOWNLOAD NOW",
            callback_data=f"deliver:{order_id}"
        )
    )

    bot.send_message(
        user_id,
        f"""🎉 <b>PAYMENT SUCCESSFUL</b>
You used wallet balance

👤 Name: {full_name}
🆔 User ID: <code>{user_id}</code>

📦 Items: {item_count}
🎬 Films: {titles_text}

🗃 Order ID:
<code>{order_id}</code>

💰 Amount Paid: ₦{amount}
⏰ Time: {now}

⬇️ DOWNLOAD NOW""",
        parse_mode="HTML",
        reply_markup=kb
    )

    # ================= NOTIFY GROUP =================
    if PAYMENT_NOTIFY_GROUP_WALLET:

        bot.send_message(
            PAYMENT_NOTIFY_GROUP_WALLET,
            f"""✅ <b>NEW PAYMENT SUCCESSFUL</b>

👤 <b>User Full Name:</b> {full_name}
🔗 <b>User Tag:</b> {tg_username}

🗃 <b>Order ID:</b>
<code>{order_id}</code>

💳 <b>Payment Method:</b> Wallet

🎬 <b>Films:</b> {titles_text}

💰 <b>Amount:</b> ₦{amount}

⏰ <b>Time:</b> {now}
""",
            parse_mode="HTML"
        )


# ==========================================
# TRANSFER MONEY START
# ==========================================

@bot.callback_query_handler(func=lambda c: c.data == "transfer_money")
def transfer_money_start(c):

    uid = c.from_user.id
    name = c.from_user.first_name or "User"

    # ===== CHECK WALLET BALANCE =====
    conn = get_wallet_conn()
    if not conn:
        bot.answer_callback_query(
            c.id,
            "Wallet error",
            show_alert=True
        )
        return

    cur = conn.cursor()

    cur.execute(
        "SELECT balance FROM wallet_balance WHERE user_id=%s",
        (uid,)
    )

    row = cur.fetchone()

    if row:
        balance = float(row[0])
    else:
        balance = 0.0

    cur.close()
    conn.close()

    # ===== IF BALANCE LESS THAN 100 =====
    if balance < 100:

        bot.answer_callback_query(
            c.id,
            f"""Malam {name}

Baka da isasshen kudi a wallet din ka.

Your balance: ₦{balance:.2f}

Domin turawa wani dole sai kana da akalla ₦100.""",
            show_alert=True
        )

        return

    # ===== CONTINUE NORMAL SYSTEM =====
    bot.answer_callback_query(c.id)

    text = """💸 TRANSFER MONEY

You can send money to your friend here.

A nan zaka iya tura kudi zuwa ga abokinka.

🆔 In ka taba Transfer Now za'a bukaci Wallet ID na abokin ka.
"""

    kb = InlineKeyboardMarkup()

    kb.row(
        InlineKeyboardButton("⬅️ Back to Wallet", callback_data="wallet_back"),
        InlineKeyboardButton("💸 Transfer Now", callback_data="start_transfer")
    )

    bot.edit_message_text(
        text,
        chat_id=uid,
        message_id=c.message.message_id,
        reply_markup=kb
    )

# ==========================================
        
# ==========================================
# TRANSFER ENTER FRIEND ID
# ==========================================

import time
import threading

TRANSFER_STAGE = {}

@bot.callback_query_handler(func=lambda c: c.data == "start_transfer")
def ask_friend_id(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id
    chat_id = c.message.chat.id
    msg_id = c.message.message_id

    # ===== START TIMER =====
    timeout = 120  # 2 minutes

    TRANSFER_STAGE[uid] = {
        "stage": "waiting_friend_id",
        "expire": time.time() + timeout,
        "msg_id": msg_id,
        "chat_id": chat_id
    }

    def countdown():

        remaining = timeout

        while remaining > 0:

            if uid not in TRANSFER_STAGE:
                return

            minutes = remaining // 60
            seconds = remaining % 60

            text = f"""💸 TRANSFER MONEY

Aiko ID na abokinka wanda kake son aikawa kudin.

Turo ID yanzu.

⏳ Time remaining: {minutes}:{seconds:02d}
"""

            try:
                bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=msg_id
                )
            except:
                pass

            time.sleep(1)
            remaining -= 1

        # ===== TIMEOUT =====
        if uid in TRANSFER_STAGE:

            del TRANSFER_STAGE[uid]

            try:
                bot.edit_message_text(
"""⌛ Transfer cancelled

Ina tsammanin ka fasa tura kudin.

⚠️ An yanke hanyar sadarwa.
Ka sake gwadawa idan kana son tura kudi.""",
                    chat_id=chat_id,
                    message_id=msg_id
                )
            except:
                pass

    threading.Thread(target=countdown, daemon=True).start()


# ==========================================
# RECEIVE FRIEND ID
# ==========================================

@bot.message_handler(func=lambda m: m.from_user.id in TRANSFER_STAGE and TRANSFER_STAGE[m.from_user.id]["stage"] == "waiting_friend_id")
def receive_friend_id(message):

    uid = message.from_user.id
    chat_id = message.chat.id
    friend_id = message.text.strip()

    # ===== CHECK NUMBER =====
    if not friend_id.isdigit():
        bot.send_message(
            chat_id,
            "❌ Wannan ba ID ba ne.\n\nTuro ID mai lamba kawai."
        )
        return

    friend_id = int(friend_id)

    # ===== PREVENT SELF TRANSFER =====
    if friend_id == uid:
        bot.send_message(
            chat_id,
            "❌ Ba zaka iya tura kudi zuwa kanka ba."
        )
        return

    # ===== GET FULL SENDER NAME =====
    sender_first = message.from_user.first_name or ""
    sender_last = message.from_user.last_name or ""
    sender_name = (sender_first + " " + sender_last).strip()

    # ===== TRY GET RECEIVER NAME =====
    try:
        user = bot.get_chat(friend_id)
        r_first = user.first_name or ""
        r_last = user.last_name or ""
        receiver_name = (r_first + " " + r_last).strip()
        if receiver_name == "":
            receiver_name = "User"
    except:
        receiver_name = "User"

    # ===== DELETE COUNTDOWN MESSAGE =====
    try:
        bot.delete_message(
            TRANSFER_STAGE[uid]["chat_id"],
            TRANSFER_STAGE[uid]["msg_id"]
        )
    except:
        pass

    # ===== SAVE FRIEND ID =====
    TRANSFER_STAGE[uid]["friend_id"] = friend_id
    TRANSFER_STAGE[uid]["stage"] = "choose_amount"

    # ===== BUTTONS =====
    kb = InlineKeyboardMarkup(row_width=2)

    kb.add(
        InlineKeyboardButton("₦100", callback_data="tr100"),
        InlineKeyboardButton("₦200", callback_data="tr200"),
        InlineKeyboardButton("₦500", callback_data="tr500"),
        InlineKeyboardButton("₦1000", callback_data="tr1000")
    )

    # ===== SEND MESSAGE =====
    bot.send_message(
        chat_id,
f"""✅ An karbi ID

👤 Sender Name: {sender_name}
🆔 Sender ID: {uid}

👤 Receiver Name: {receiver_name}
🆔 Receiver ID: {friend_id}

Zabi adadin kudin da zaka tura masa.
""",
        reply_markup=kb
    )

# ==========================================
# TRANSFER AMOUNT SELECTED
# ==========================================

from psycopg2.extras import RealDictCursor

@bot.callback_query_handler(func=lambda c: c.data.startswith("tr"))
def transfer_amount_handler(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id
    chat_id = c.message.chat.id
    msg_id = c.message.message_id

    if uid not in TRANSFER_STAGE:
        return

    try:
        amount = int(c.data.replace("tr", ""))
    except:
        return

    friend_id = TRANSFER_STAGE[uid].get("friend_id")
    friend_name = TRANSFER_STAGE[uid].get("friend_name", "User")

    # ===== CHECK BALANCE =====
    conn = get_wallet_conn()
    if not conn:
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT balance FROM wallet_balance WHERE user_id=%s",
        (uid,)
    )

    row = cur.fetchone()

    balance = int(row["balance"]) if row else 0

    # ===== INSUFFICIENT BALANCE =====
    if balance < amount:

        text = f"""❌ Insufficient wallet balance

Your balance: ₦{balance}
Transfer amount: ₦{amount}

Please add money to your wallet."""

        try:
            bot.edit_message_text(
                text,
                chat_id=chat_id,
                message_id=msg_id
            )
        except:
            pass

        cur.close()
        conn.close()
        return

    # ===== SAVE AMOUNT =====
    TRANSFER_STAGE[uid]["amount"] = amount

    # ===== CONFIRM MESSAGE =====
    text = f"""💸 Confirm Transfer

Are you sure you want to send money?

👤 Receiver: {friend_name}
🆔 User ID: {friend_id}

💰 Amount: ₦{amount}

Please confirm to continue."""

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "✅ Confirm Transfer",
            callback_data="confirm_transfer"
        )
    )

    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=kb
        )
    except:
        pass

    cur.close()
    conn.close()
    
# ==========================================
# CONFIRM TRANSFER
# ==========================================

from psycopg2.extras import RealDictCursor
from datetime import datetime


TRANSFER_LOCK = set()

@bot.callback_query_handler(func=lambda c: c.data == "confirm_transfer")
def confirm_transfer(c):

    bot.answer_callback_query(c.id)

    uid = c.from_user.id
    chat_id = c.message.chat.id
    msg_id = c.message.message_id
    sender_name = c.from_user.first_name or "User"
    sender_username = c.from_user.username or "None"

    # ===== PREVENT DOUBLE CLICK =====
    if uid in TRANSFER_LOCK:
        return

    TRANSFER_LOCK.add(uid)

    if uid not in TRANSFER_STAGE:
        TRANSFER_LOCK.discard(uid)
        return

    friend_id = TRANSFER_STAGE[uid].get("friend_id")
    friend_name = TRANSFER_STAGE[uid].get("friend_name","User")
    amount = int(TRANSFER_STAGE[uid].get("amount",0))

    if not friend_id or amount <= 0:
        TRANSFER_LOCK.discard(uid)
        return

    conn = get_wallet_conn()
    if not conn:
        TRANSFER_LOCK.discard(uid)
        return

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        conn.autocommit = False

        # ===== LOCK BALANCE =====
        cur.execute(
            "SELECT balance FROM wallet_balance WHERE user_id=%s FOR UPDATE",
            (uid,)
        )

        row = cur.fetchone()
        sender_balance = int(row["balance"]) if row else 0

        if sender_balance < amount:

            conn.rollback()

            bot.edit_message_text(
f"""❌ Transfer failed

Your balance is not enough.

Balance: ₦{sender_balance}
Amount: ₦{amount}""",
                chat_id=chat_id,
                message_id=msg_id
            )

            TRANSFER_LOCK.discard(uid)
            return

        # ===== DEDUCT SENDER =====
        cur.execute(
            """
            UPDATE wallet_balance
            SET balance = balance - %s
            WHERE user_id=%s
            """,
            (amount, uid)
        )

        # ===== ADD RECEIVER =====
        cur.execute(
            """
            INSERT INTO wallet_balance (user_id, balance)
            VALUES (%s,%s)
            ON CONFLICT (user_id)
            DO UPDATE SET balance = wallet_balance.balance + %s
            """,
            (friend_id, amount, amount)
        )

        # ===== TRANSACTION LOG =====
        cur.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, amount, type, description)
            VALUES (%s,%s,'transfer_out','Money sent')
            """,
            (uid, amount)
        )

        cur.execute(
            """
            INSERT INTO wallet_transactions
            (user_id, amount, type, description)
            VALUES (%s,%s,'transfer_in','Money received')
            """,
            (friend_id, amount)
        )

        conn.commit()

    except Exception:

        conn.rollback()

        bot.edit_message_text(
"""❌ Transfer failed

Network error occurred.
Please try again.""",
            chat_id=chat_id,
            message_id=msg_id
        )

        cur.close()
        conn.close()

        TRANSFER_LOCK.discard(uid)
        return

    cur.close()
    conn.close()

    # ===== REMOVE SESSION =====
    if uid in TRANSFER_STAGE:
        del TRANSFER_STAGE[uid]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ===== RECEIVER MESSAGE =====
    try:
        bot.send_message(
            friend_id,
f"""💰 You received money from your friend

👤 Sender: {sender_name}
🆔 User ID: {uid}

💵 Amount: ₦{amount}

⏰ Time: {now}"""
        )
    except:
        pass

    # ===== EDIT MESSAGE (SENDER) =====
    bot.edit_message_text(
f"""🎉 Great!

You sent ₦{amount} to your friend.

👤 Name: {friend_name}
🆔 User ID: {friend_id}

💵 Amount: ₦{amount}

⏰ Time: {now}""",
        chat_id=chat_id,
        message_id=msg_id
    )

    # ===== ADMIN NOTIFY =====
    try:
        bot.send_message(
            ADMIN_ID,
f"""💸 New Wallet Transfer

User {sender_name} sent ₦{amount} to his friend.

Sender:
Name: {sender_name}
Username: @{sender_username}
ID: {uid}

Receiver:
Name: {friend_name}
ID: {friend_id}

Time: {now}

Status: SUCCESS"""
        )
    except:
        pass

    # ===== RELEASE LOCK =====
    TRANSFER_LOCK.discard(uid)    
#=========================================================
@bot.message_handler(
    func=lambda m: (
        m.text
        and m.text.startswith("/start ")
        and len(m.text.split(" ", 1)) > 1
        and m.text.split(" ", 1)[1].startswith("howto_")
    )
)
def __hard_start_howto(msg):
    """
    Wannan handler:
    - Yana rike howto_ deeplink
    - Yana hana komawa main /start
    - Yana kira howto_start_handler kai tsaye
    """
    return howto_start_handler(msg)
# ================= HOW TO BUY STATE =================
HOWTO_STATE = {}


# ======================================================
# /update  (ADMIN ONLY)
# ======================================================
@bot.message_handler(commands=["update"])
def update_howto_cmd(m):
    if m.from_user.id != ADMIN_ID:
        return

    HOWTO_STATE[m.from_user.id] = {"stage": "hausa"}

    bot.send_message(
        m.chat.id,
        "✍️ <b>Rubuta HAUSA version cikakke:</b>",
        parse_mode="HTML"
    )


# ======================================================
# UPDATE FLOW (HAUSA → ENGLISH → MEDIA)
# ======================================================
@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.from_user.id in HOWTO_STATE,
    content_types=["text", "video", "document", "photo"]
)
def howto_update_flow(m):
    state = HOWTO_STATE.get(m.from_user.id)
    if not state:
        return

    stage = state["stage"]

    # ---------- HAUSA ----------
    if stage == "hausa":
        if m.content_type != "text":
            bot.send_message(m.chat.id, "❌ Hausa text kawai ake bukata.")
            return
        state["hausa_text"] = m.text
        state["stage"] = "english"
        bot.send_message(
            m.chat.id,
            "✍️ <b>Rubuta ENGLISH version:</b>",
            parse_mode="HTML"
        )
        return

    # ---------- ENGLISH ----------
    if stage == "english":
        if m.content_type != "text":
            bot.send_message(m.chat.id, "❌ English text kawai ake bukata.")
            return
        state["english_text"] = m.text
        state["stage"] = "media"
        bot.send_message(
            m.chat.id,
            "🎬 Turo <b>VIDEO / DOCUMENT / PHOTO</b>:",
            parse_mode="HTML"
        )
        return

    # ---------- MEDIA ----------
    if stage == "media":
        file_id = None
        media_type = None

        if m.content_type == "video":
            file_id = m.video.file_id
            media_type = "video"
        elif m.content_type == "document":
            file_id = m.document.file_id
            media_type = "document"
        elif m.content_type == "photo":
            file_id = m.photo[-1].file_id
            media_type = "photo"
        else:
            bot.send_message(m.chat.id, "❌ Media bai dace ba.")
            return

        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT MAX(version) FROM how_to_buy")
            last_version = cur.fetchone()[0] or 0

            cur.execute(
                """
                INSERT INTO how_to_buy
                (hausa_text, english_text, media_file_id, media_type, version)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    state["hausa_text"],
                    state["english_text"],
                    file_id,
                    media_type,
                    last_version + 1
                )
            )

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            try:
                conn.rollback()
            except:
                pass
            print("HOWTO UPDATE ERROR:", e)
            return

        HOWTO_STATE.pop(m.from_user.id, None)

        bot.send_message(
            m.chat.id,
            "✅ <b>HOW TO BUY an sabunta successfully</b>",
            parse_mode="HTML"
        )


# ======================================================
@bot.message_handler(content_types=['new_chat_members'])
def get_group_id(message):

    try:
        chat_id = message.chat.id
        chat_title = message.chat.title or "Unknown"

        bot.send_message(
            ADMIN_ID,
            f"""✅ GROUP DETECTED

📛 Name: {chat_title}
🆔 ID:
<code>{chat_id}</code>
""",
            parse_mode="HTML"
        )

    except:
        pass


# /post  (ADMIN ONLY)



# ======================================================
@bot.message_handler(commands=["post"])
def post_to_channel(m):
    if m.from_user.id != ADMIN_ID:
        return

    cur.execute(
        """
        SELECT version
        FROM how_to_buy
        ORDER BY version DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()

    if not row:
        bot.send_message(m.chat.id, "❌ Babu HOW TO BUY da aka saita tukuna.")
        return

    version = row[0]
    deeplink = f"https://t.me/{BOT_USERNAME}?start=howto_{version}"

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            "👉 Click here",
            url=deeplink
        )
    )

    bot.send_message(
        CHANNEL,
        " <b>👀🤝\n\n 🤩Kada ka bari a baka labari! Koyi yadda zaka siya 🎬 fim a  cikin sauri, sauƙi kuma babu wahala\n\n Cikin aminci 100% ba tare da jira ko damuwa ba 🥰\n\n\n 🤖@Algaitabot\n\nDANNA (Click here) 🔥\n\n🔰🔰🔰🔰🔰</b>",
        parse_mode="HTML",
        reply_markup=kb
    )

    bot.send_message(m.chat.id, "✅ An tura post zuwa channel.")




# ======================================================
# HOW TO START (HOWTO ONLY)
# ======================================================

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/start howto_"))
def howto_start_handler(m):

    args = m.text.split()

    # kariya
    if len(args) < 2 or not args[1].startswith("howto_"):
        return

    try:
        version = int(args[1].split("_")[1])
    except Exception:
        return

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT hausa_text, english_text, media_file_id, media_type
            FROM how_to_buy
            WHERE version=%s
            """,
            (version,)
        )
        row = cur.fetchone()
        cur.close()
    except Exception:
        return

    if not row:
        bot.send_message(m.chat.id, "❌ Wannan version bai wanzu ba.")
        return

    hausa_text, english_text, file_id, media_type = row

    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🇬🇧 English", callback_data=f"howto_en:{version}"),
        types.InlineKeyboardButton("🇳🇬 Hausa", callback_data=f"howto_ha:{version}")
    )

    caption = hausa_text

    try:
        if media_type == "video":
            bot.send_video(m.chat.id, file_id, caption=caption, reply_markup=kb)
        elif media_type == "document":
            bot.send_document(m.chat.id, file_id, caption=caption, reply_markup=kb)
        else:
            bot.send_photo(m.chat.id, file_id, caption=caption, reply_markup=kb)
    except Exception:
        return


# ======================================================
# LANGUAGE SWITCH (EDIT ONLY)
# ======================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("howto_"))
def howto_language_switch(c):

    try:
        lang, version = c.data.split(":")
        version = int(version)
    except Exception:
        return

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT hausa_text, english_text
            FROM how_to_buy
            WHERE version=%s
            """,
            (version,)
        )
        row = cur.fetchone()
        cur.close()
    except Exception:
        return

    if not row:
        bot.answer_callback_query(c.id, "❌ Version bai wanzu ba.")
        return

    hausa_text, english_text = row
    text = english_text if lang == "howto_en" else hausa_text

    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🇬🇧 English", callback_data=f"howto_en:{version}"),
        types.InlineKeyboardButton("🇳🇬 Hausa", callback_data=f"howto_ha:{version}")
    )

    try:
        bot.edit_message_caption(
            chat_id=c.message.chat.id,
            message_id=c.message.message_id,
            caption=text,
            reply_markup=kb
        )
    except Exception:
        pass

    bot.answer_callback_query(c.id)


@bot.message_handler(commands=["sales"])
def admin_sales_command(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    now = _ng_now()
    since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    send_sales_report(
        since,
        f"📊 MONTHLY SALES REPORT ({now.strftime('%B %Y')})",
        ADMIN_ID,
        silent_if_empty=False
    )

# --- Added callback handler for in-bot "View All Movies" buttons ---
@bot.callback_query_handler(func=lambda c: c.data in ("view_all_movies","viewall"))
def _callback_view_all(call):
    uid = call.from_user.id
    # Build a small message-like object expected by send_weekly_list
    class _Msg:
        def __init__(self, uid):
            self.chat = type('X', (), {'id': uid})
            self.text = ""
    try:
        send_weekly_list(_Msg(uid))
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "An samu matsala wajen nuna jerin.")

 #======================================================

# ========= HARD START BUYD =========
@bot.message_handler(
    func=lambda m: m.text
    and m.text.startswith("/start ")
    and m.text.split(" ", 1)[1].startswith("buyd_")
)
def __hard_start_buyd(msg):
    return buyd_deeplink_handler(msg)


# ========= HARD START GROUPITEM =========
@bot.message_handler(
    func=lambda m: m.text
    and m.text.startswith("/start ")
    and m.text.split(" ", 1)[1].startswith("groupitem_")
)
def __hard_start_groupitem(msg):
    return groupitem_deeplink_handler(msg)

# --- Added deep-link start handler for viewall/weakupdate (runs before other start handlers) ---  
@bot.message_handler(func=lambda m: (m.text or "").strip().split(" ")[0]=="/start" and len((m.text or "").strip().split(" "))>1 and (m.text or "").strip().split(" ")[1] in ("viewall","weakupdate"))  
def _start_deeplink_handler(msg):  
    """  
    Catch /start viewall or /start weakupdate deep-links from channel posts.  
    This handler tries to send the weekly list directly and then returns without invoking the normal start flow.  
    Placed early to take precedence over other start handlers.  
    """  
    try:  
        send_weekly_list(msg)  
    except Exception as e:  
        try:  
            bot.send_message(msg.chat.id, "An samu matsala wajen nuna weekly list.")  
        except:  
            pass  
    return




# ================== END RUKUNI B ==================



# --- Added callback handler for in-bot "View All Movies" buttons ---
@bot.callback_query_handler(func=lambda c: c.data in ("view_all_movies","viewall"))
def _callback_view_all(call):
    uid = call.from_user.id
    # Build a small message-like object expected by send_weekly_list
    class _Msg:
        def __init__(self, uid):
            self.chat = type('X', (), {'id': uid})
            self.text = ""
    try:
        send_weekly_list(_Msg(uid))
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "An samu matsala wajen nuna jerin.")





# ========== HELPERS ==========
def check_join(uid):
    try:
        member = bot.get_chat_member(CHANNEL, uid)
        return member.status in ("member", "administrator", "creator", "restricted")
    except Exception:
        return False

# name anonymization
def mask_name(fullname):
    """Mask parts of the name as requested: Muhmad, Khid, Sa*i style."""
    if not fullname:
        return "User"
    s = re.sub(r"\s+", " ", fullname.strip())
    # split on non-alphanumeric to preserve parts
    parts = re.split(r'(\W+)', s)
    out = []
    for p in parts:
        if not p or re.match(r'\W+', p):
            out.append(p)
            continue
        # p is a word
        n = len(p)
        if n <= 2:
            out.append(p[0] + "*"*(n-1))
            continue
        # keep first 2 and last 1, hide middle with **
        if n <= 4:
            keep = p[0] + "*"*(n-2) + p[-1]
            out.append(keep)
        else:
            # first two, two stars, last one
            out.append(p[:2] + "**" + p[-1])
    return "".join(out)

def tr_user(uid, key, default=""):
    return default

#farko
def reply_menu(uid=None):
    kb = InlineKeyboardMarkup()

    # ===== WALLET (TOP BUTTON) =====
    kb.add(
        InlineKeyboardButton("🏦MY WALLET💵", callback_data="wallet")
    )

    # ===== Labels =====
    paid_orders_label = "🗂Paid Orders"
    my_orders_label   = "Pending order"

    cart_label    = tr_user(uid, "btn_cart", default="Check cart")
    films_label   = "🎬Check Films"
    support_label = tr_user(uid, "btn_support", default="📞Help Center")
    channel_label = tr_user(uid, "btn_channel", default="🏘Our Channel")

    # ===== ROW 1 (PAID + MY ORDERS) =====
    kb.row(
        InlineKeyboardButton(paid_orders_label, callback_data="paid_orders"),
        InlineKeyboardButton(my_orders_label, callback_data="myorders_new")
    )

    # ===== ROW 2 (CHECK FILMS + SUPPORT) =====
    kb.row(
        InlineKeyboardButton(
            films_label,
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        ),
        InlineKeyboardButton(
            support_label,
            url=f"https://t.me/{ADMIN_USERNAME}"
        )
    )

    # ===== ROW 3 (OUR CHANNEL + CHECK CART) =====
    kb.row(
        InlineKeyboardButton(
            channel_label,
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        ),
        InlineKeyboardButton(
            cart_label,
            callback_data="viewcart"
        )
    )

    # ===== ROW 4 (VIP GROUP) =====
    kb.add(
        InlineKeyboardButton("💎 VIP GROUP", callback_data="vipgroup")
    )

    # ===== ADMIN ONLY BUTTONS =====
    if uid in ADMINS:
        kb.add(
            InlineKeyboardButton("🏛SERIES&MOV🌐", callback_data="groupitems")
        )

    return kb
# end


def user_main_menu(uid=None):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)

    cart_label = tr_user(uid, "btn_cart", default="Check cart")
    help_label = tr_user(uid, "btn_help", default="HELP")
    vip_label = "🔐VIP GROUP"
    done_label = "Done"
    wallet_label = "🏦My wallet💰"

    # ===== MY WALLET a sama =====
    kb.row(
        KeyboardButton(wallet_label)
    )

    # ===== VIP GROUP a kasa kadan =====
    kb.row(
        KeyboardButton(vip_label)
    )

    # ===== HELP da CART a layi daya =====
    if str(uid) == str(ADMIN_ID):   # 🔐 Admin only check
        kb.row(
            KeyboardButton(help_label),
            KeyboardButton(cart_label),
            KeyboardButton(done_label)   # Admin kaɗai zai gani
        )
    else:
        kb.row(
            KeyboardButton(help_label),
            KeyboardButton(cart_label)
        )

    return kb



#Start
def movie_buttons_inline(mid, user_id=None):
    kb = InlineKeyboardMarkup()

    add_cart = tr_user(user_id, "btn_add_cart", default="➕ Add to Cart")
    buy_now  = tr_user(user_id, "btn_buy_now", default="💳 Buy Now")
    channel  = tr_user(user_id, "btn_channel", default="🏘Our Channel")

    kb.add(
        InlineKeyboardButton(add_cart, callback_data=f"addcartdm:{mid}"),
        InlineKeyboardButton(
            buy_now,
            url=f"https://t.me/{BOT_USERNAME}?start=buyd_{mid}"
        )
    )
#end
    # 🛑 Idan user_id == None → channel ne → kada a ƙara sauran buttons
    if user_id is None:
        return kb

    # 🔰 Idan private chat ne → saka sauran buttons
    kb.row(
        
        InlineKeyboardButton(channel, url=f"https://t.me/{CHANNEL.lstrip('@')}")
    )

  

    return kb
#END

# ========== START ==========
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    fname = message.from_user.first_name or ""
    uname = f"@{message.from_user.username}" if message.from_user.username else "Babu username"
    text = (message.text or "").strip()

    # ========= REF =========
    param = None
    if text.startswith("/start "):
        param = text.split(" ", 1)[1].strip()
    elif text.startswith("/start"):
        parts = text.split(" ", 1)
        if len(parts) > 1:
            param = parts[1].strip()

    if param and param.startswith("ref"):
        try:
            ref_id = int(param[3:])
            add_referral(ref_id, uid)
            try:
                bot.send_message(
                    ref_id,
                    f"Someone used your invite link! ID: <code>{uid}</code>",
                    parse_mode="HTML"
                )
            except Exception as e:
                pass
        except Exception as e:
            pass

    # ========= ADMIN NOTIFY =========
    try:
        bot.send_message(
            ADMIN_ID,
            f"🟢 SABON VISITOR!\n\n"
            f"👤 Sunan: <b>{fname}</b>\n"
            f"🔗 Username: {uname}\n"
            f"🆔 ID: <code>{uid}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        print("Failed to notify admin about visitor:", e)

    # ========= JOIN CHECK =========
    try:
        joined = check_join(uid)
    except Exception as e:
        joined = False


    # ❌ IDAN BAI SHIGA BA
    if not joined:
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "Join Channel",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        )
        kb.add(
            InlineKeyboardButton(
                "I've Joined✅",
                callback_data="checkjoin"
            )
        )
        bot.send_message(
            uid,
            "⚠️ Kafin ka ci gaba, dole ne ka shiga channel ɗinmu.",
            reply_markup=kb
        )
        return

    # ========= MENUS =========
    bot.send_message(
        uid,
        "Abokin hulɗa, muna farin cikin maraba da kai na zuwa shagon fina-finanmu.",
        reply_markup=user_main_menu(uid)
    )
    bot.send_message(
        uid,
        "Shagon Algaita Movie Store na kawo maka zaɓaɓɓun fina-finai masu inganci. Mun tace su tsaf daga ɗanyen kaya, mun ware mafi kyau kawai. Duk fim ɗin da ka siya a nan, tabbas ba za mu ba ka kunya ba.\n\n Muna kawo fina-finan kowanne kamfanin fassara anan.",
        reply_markup=reply_menu(uid)
    )


# ========= CHECK JOIN CALLBACK =========
@bot.callback_query_handler(func=lambda call: call.data == "checkjoin")
def checkjoin_callback(call):
    uid = call.from_user.id
    fname = call.from_user.first_name or ""

    try:
        joined = check_join(uid)
    except Exception as e:
        joined = False

    if not joined:
        bot.answer_callback_query(
            call.id,
            f"Malam {fname}\n\nHar yanzu baka shiga channel ɗinmu ba.\nDa fatan za ka shiga kafin ka ci gaba.",
            show_alert=True
        )
        return

    bot.answer_callback_query(call.id)

    # 👇 NAN NE GYARAN DA YA HANA BOT YA KIRA KANSA
    class FakeMessage:
        def __init__(self, user):
            self.from_user = user
            self.text = "/start"

    fake_message = FakeMessage(call.from_user)

    try:
        start(fake_message)
    except Exception as e:
        bot.send_message(ADMIN_ID, f"ERROR calling start():\n{e}")


# ======================================
# ======================================
# TEXT BUTTON HANDLER (GLOBAL SAFE)
# ======================================
@bot.message_handler(
    func=lambda msg: (
        isinstance(getattr(msg, "text", None), str)
        and msg.text.strip() in ["HELP", "Check cart", "🔐VIP GROUP", "🏦My wallet💰"]
    )
)
def user_buttons(message):

    txt = message.text.strip()
    uid = str(message.from_user.id)   # 🔐 STRING FOR POSTGRES


    # ======= HELP =======
    if txt == "HELP":

        kb = InlineKeyboardMarkup()

        if ADMIN_USERNAME:
            kb.add(
                InlineKeyboardButton(
                    "Contact Admin",
                    url=f"https://t.me/{ADMIN_USERNAME}"
                )
            )

        try:
            bot.send_message(
                message.chat.id,
                "Need help? Contact the admin.",
                reply_markup=kb
            )

        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ HELP ERROR:\nType: {type(e).__name__}\nMsg: {str(e)}"
            )

        return


    # ======= CHECK CART =======
    if txt == "Check cart":

        try:
            show_cart(message.chat.id, uid)

        except Exception as e:

            import traceback
            error_details = traceback.format_exc()

            bot.send_message(
                message.chat.id,
                f"❌ CHECK CART ERROR\n\n"
                f"Type: {type(e).__name__}\n"
                f"Message: {str(e)}\n\n"
                f"Full Trace:\n{error_details[:3000]}"
            )

            bot.send_message(
                message.chat.id,
                "⚠️ An samu matsala wajen bude cart."
            )

        return


    # ======= VIP GROUP =======
    if txt == "🔐VIP GROUP":

        class CallMock:
            def __init__(self, msg):
                self.id = "vip_text_button"
                self.from_user = msg.from_user
                self.message = msg

        vip_group_info(CallMock(message))
        return


    # ======= MY WALLET =======
    if txt == "🏦My wallet💰":

        class CallMock:
            def __init__(self, msg):
                self.id = "wallet_text_button"
                self.from_user = msg.from_user
                self.message = msg

        try:
            # kira asalin wallet block
            open_wallet(CallMock(message))

        except Exception as e:

            import traceback
            error_details = traceback.format_exc()

            bot.send_message(
                message.chat.id,
                f"❌ WALLET ERROR\n\n"
                f"Type: {type(e).__name__}\n"
                f"Message: {str(e)}\n\n"
                f"Trace:\n{error_details[:3000]}"
            )

        return




# ======================================
# ======================================

# ======================================
# CLEAR CART
# ======================================
def clear_cart(uid):
    uid = str(uid)
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM cart WHERE user_id = %s",
            (uid,)
        )
        conn.commit()
        cur.close()
    except Exception as e:
        conn.rollback()
        print("CLEAR CART ERROR:", e)

# ======================================
# GET CART (POSTGRES SAFE)
# ======================================
def get_cart(uid):
    uid = str(uid)
    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.item_id,
                i.title,
                i.price,
                i.file_id
            FROM cart c
            JOIN items i ON i.id = c.item_id
            WHERE c.user_id = %s
            ORDER BY c.id DESC
        """, (uid,))

        rows = cur.fetchall()
        return rows

    except Exception as e:
        print("GET_CART ERROR:", e)
        return []

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
# ======================================
def get_credits_for_user(user_id):
    return 0, []


# ======================================
# PARSE CAPTION (TITLE + PRICE)
# ======================================
def parse_caption_for_title_price(text):
    if not text:
        return None, None

    text = text.replace("₦", "").strip()

    m = re.match(r"^(.*?)[\s\-]+(\d+)$", text)
    if m:
        return m.group(1).strip(), int(m.group(2))

    parts = text.splitlines()
    if len(parts) >= 2 and parts[1].strip().isdigit():
        return parts[0].strip(), int(parts[1].strip())

    return None, None

@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.from_user.id in admin_states
)
def admin_inputs(message):
    try:
        state_entry = admin_states.get(message.from_user.id)
        if not state_entry:
            return

        state = state_entry.get("state")

        # ⚠️ NOTE:
        # An cire ADD MOVIE logic, amma sauran admin states
        # (weak_update, update_week, da sauransu)
        # suna nan a sauran code ɗinka

        return

    except Exception as e:
        print("ADMIN INPUT ERROR:", e)
        return




    # ========== CANCEL ==========
@bot.message_handler(commands=["cancel"])
def cancel_cmd(message):
    if message.from_user.id == ADMIN_ID and admin_states.get(ADMIN_ID) and admin_states[ADMIN_ID].get("state") in ("weak_update", "update_week"):
        inst = admin_states[ADMIN_ID]
        inst_msg_id = inst.get("inst_msg_id")
        if inst_msg_id:
            try:
                bot.delete_message(chat_id=ADMIN_ID, message_id=inst_msg_id)
            except Exception as e:
                print("Failed to delete instruction message on cancel:", e)
        admin_states.pop(ADMIN_ID, None)
        bot.reply_to(message, "An soke Update/Weak update kuma an goge sakon instruction.")
        return

    if message.from_user.id == ADMIN_ID and admin_states.get(ADMIN_ID):
        admin_states.pop(ADMIN_ID, None)
        bot.reply_to(message, "An soke aikin admin na yanzu.")
        return



# ==================================================
# ==================================================
def get_cart(uid):
    uid = str(uid)  # 🔐 MUHIMMI

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                c.item_id,
                i.title,
                i.price,
                i.file_id,
                i.group_key
            FROM cart c
            JOIN items i ON i.id = c.item_id
            WHERE c.user_id = %s
            """,
            (uid,)
        )
        rows = cur.fetchall()
        cur.close()
        return rows

    except Exception as e:
        # 🔥 DEBUG MAI KARFI
        print("GET_CART ERROR:", e)
        return []
# End


# # ========== BUILD CART VIEW (GROUP-AWARE - FIXED & SAFE) ==========
def build_cart_view(uid):
    uid = str(uid)  # 🔐 MUHIMMI
    rows = get_cart(uid)

    kb = InlineKeyboardMarkup()

    # ===== IDAN CART BABU KOMAI =====
    if not rows:
        text = (
            "<b>You haven’t added any items to your cart yet.\n\n"
            "Check our channel to buy movie.</b>"
        )

        kb.row(
            InlineKeyboardButton(
                "🏘 Our Channel",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        )
        return text, kb

    total = 0
    lines = []

    # ===============================
    # GROUP ITEMS BY GROUP_KEY
    # ===============================
    grouped = {}

    for movie_id, title, price, file_id, group_key in rows:
        key = group_key or f"single_{movie_id}"

        if key not in grouped:
            grouped[key] = {
                "ids": [],
                "title": title or "🧺 Group / Series Item",
                "price": int(price or 0),
                "group_key": group_key
            }

        grouped[key]["ids"].append(movie_id)

    # ===============================
    # DISPLAY ITEMS
    # ===============================
    for key, g in grouped.items():
        ids = g["ids"]
        title = g["title"]
        price = g["price"]
        group_key = g["group_key"]

        total += price
        lines.append(f"🎬 {title} — ₦{price}")

        # ===== SAFE CALLBACK DATA =====
        if group_key:
            # use group_key only (SHORT & SAFE)
            callback_value = group_key
        else:
            # single item → use id
            callback_value = ids[0]

        kb.add(
            InlineKeyboardButton(
                f"❌ Remove: {title}",
                callback_data=f"removecart:{callback_value}"
            )
        )

    # ===== TOTAL =====
    lines.append("")
    lines.append(f"<b>Total:</b> ₦{total}")

    text = (
        "🛒 <b>Your cart list.</b>\n\n"
        + "\n".join(lines)
    )

    # ===== ACTION BUTTONS =====
    kb.row(
        InlineKeyboardButton("🧹 Clear Cart", callback_data="clearcart"),
        InlineKeyboardButton("💵 CHECKOUT", callback_data="checkout")
    )

    # ===== OUR CHANNEL BUTTON =====
    kb.row(
        InlineKeyboardButton(
            "🏘 Our Channel",
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        )
    )

    return text, kb
    # ================= USER RESEND SEARCH (USING user_movies) =================

@bot.message_handler(
    func=lambda m: m.from_user.id in admin_states
    and admin_states.get(m.from_user.id, {}).get("state") in (
        "search_menu",
        "browse_menu",
        "series_menu",
        "search_trending",
    )
)
def ignore_unexpected_text(m):
    uid = m.from_user.id
    bot.send_message(
        uid,
        "ℹ️ Don Allah ka yi amfani da *buttons* da ke ƙasa.",
        parse_mode="Markdown"
    )
# ======================================================
# ACTIVE BUYERS (ADMIN ONLY | PAGINATION | EDIT MODE)

from psycopg2.extras import RealDictCursor

# ================== CANCEL ORDER (POSTGRES | SAFE | EDIT MESSAGE) ==================
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("cancel:"))
def cancel_order_handler(c):
    uid = c.from_user.id
    bot.answer_callback_query(c.id)

    try:
        order_id = c.data.split("cancel:", 1)[1]
    except Exception:
        return

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 🔎 Tabbatar order na wannan user ne kuma unpaid
    try:
        cur.execute(
            """
            SELECT id
            FROM orders
            WHERE id=%s
              AND user_id=%s
              AND paid=0
            """,
            (order_id, uid)
        )
        order = cur.fetchone()
    except Exception:
        cur.close()
        conn.close()
        return

    if not order:
        try:
            bot.edit_message_text(
                "❌ <b>Ba a sami order ba ko kuma an riga an biya shi.</b>",
                chat_id=uid,
                message_id=c.message.message_id,
                parse_mode="HTML"
            )
        except:
            pass

        cur.close()
        conn.close()
        return

    # 🧹 Goge order_items gaba ɗaya
    try:
        cur.execute(
            "DELETE FROM order_items WHERE order_id=%s",
            (order_id,)
        )

        # 🧹 Goge order
        cur.execute(
            "DELETE FROM orders WHERE id=%s",
            (order_id,)
        )

        conn.commit()
    except Exception:
        conn.rollback()
        cur.close()
        conn.close()
        return

    # ✏️ EDIT ORIGINAL MESSAGE INSTEAD OF SENDING NEW ONE
    try:
        bot.edit_message_text(
            "❌ <b>An soke wannan order ɗin.</b>",
            chat_id=uid,
            message_id=c.message.message_id,
            parse_mode="HTML"
        )
    except:
        pass

    cur.close()
    conn.close()




# ================== END RUKUNI B ==================
@bot.message_handler(commands=["sales"])
def admin_sales_command(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    now = _ng_now()
    since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    send_sales_report(
        since,
        f"📊 MONTHLY SALES REPORT ({now.strftime('%B %Y')})",
        ADMIN_ID,
        silent_if_empty=False
    )

# --- Added callback handler for in-bot "View All Movies" buttons ---
@bot.callback_query_handler(func=lambda c: c.data in ("view_all_movies","viewall"))
def _callback_view_all(call):
    uid = call.from_user.id
    # Build a small message-like object expected by send_weekly_list
    class _Msg:
        def __init__(self, uid):
            self.chat = type('X', (), {'id': uid})
            self.text = ""
    try:
        send_weekly_list(_Msg(uid))
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, "An samu matsala wajen nuna jerin.")





# ========== HELPERS =======
# ========== detect forwarded channel post ==========
@bot.message_handler(
    func=lambda m: getattr(m, "forward_from_chat", None) is not None
    or getattr(m, "forward_from_message_id", None) is not None
)
def handle_forwarded_post(m):
    fc = getattr(m, "forward_from_chat", None)
    fid = getattr(m, "forward_from_message_id", None)

    if not fc and not fid:
        return

    try:
        chat_info = ""

        if fc:
            if getattr(fc, "username", None):
                chat_info = f"@{fc.username}"
            else:
                chat_info = f"chat_id:{fc.id}"
        else:
            chat_info = "Unknown channel"

        if fid:
            bot.reply_to(
                m,
                f"Original channel: {chat_info}\nOriginal message id: {fid}"
            )
        else:
            bot.reply_to(
                m,
                f"Original channel: {chat_info}\nMessage id not found."
            )

    except Exception as e:
        print("forward handler error:", e)


# ========== show_cart ==========
# ========== show_cart ==========
def show_cart(chat_id, user_id):

    user_id = str(user_id)   # 🔐 MUHIMMI

    rows = get_cart(user_id)

    kb = InlineKeyboardMarkup()

    # ===== IDAN CART EMPTY =====
    if not rows:
        kb.row(
            InlineKeyboardButton(
                "🏘Our Channel",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        )

        s = tr_user(
            user_id,
            "cart_empty",
            default="You haven’t added any items to your cart yet,\n\nCheck our channel to buy movie."
        )

        msg = bot.send_message(chat_id, s, reply_markup=kb)
        cart_sessions[str(user_id)] = msg.message_id
        return

    text_lines = ["🛒 <b>Your cart list.</b>"]
    total = 0

    # ===============================
    # GROUP ITEMS BY group_key
    # ===============================
    grouped = {}

    for row in rows:

        # 🔥 SAFE UNPACK
        if len(row) == 5:
            movie_id, title, price, file_id, group_key = row
        else:
            # idan group_key babu
            movie_id, title, price, file_id = row
            group_key = None

        key = group_key if group_key else f"single_{movie_id}"

        if key not in grouped:
            grouped[key] = {
                "ids": [],
                "title": title or "📦 Group / Series Item",
                "price": int(price or 0)
            }

        grouped[key]["ids"].append(movie_id)

    # ===============================
    # DISPLAY ITEMS
    # ===============================
    for key, g in grouped.items():
        ids = g["ids"]
        title = g["title"]
        price = int(g["price"] or 0)

        total += price

        if price > 0:
            text_lines.append(f"• {title} — ₦{price}")
        else:
            text_lines.append(f"• {title} — 📦 Series")

        # 🔥 VERY IMPORTANT (Telegram limit 64 chars)
        ids_str = "_".join(str(i) for i in ids)

        if len(ids_str) > 40:
            # idan yayi tsawo, amfani da key maimakon ids
            ids_str = str(key)[:40]

        kb.add(
            InlineKeyboardButton(
                f"❌ Remove: {title[:18]}",
                callback_data=f"removecart:{ids_str}"
            )
        )

    text_lines.append(f"\n<b>Total:</b> ₦{total}")

    # ===============================
    # ACTION BUTTONS
    # ===============================
    kb.row(
        InlineKeyboardButton("🧹 Clear Cart", callback_data="clearcart"),
        InlineKeyboardButton("💵 CHECKOUT", callback_data="checkout")
    )

    kb.row(
        InlineKeyboardButton(
            "🏘Our Channel",
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        )
    )

    msg = bot.send_message(
        chat_id,
        "\n".join(text_lines),
        reply_markup=kb,
        parse_mode="HTML"
    )

    cart_sessions[str(user_id)] = msg.message_id
# ---------- weekly button ----------
@bot.callback_query_handler(func=lambda c: c.data == "weekly_films")
def send_weekly_films(call):
    return send_weekly_list(call.message)


# ---------- My Orders (UNPAID with per-item REMOVE | OWNERSHIP SAFE) ----------
ORDERS_PER_PAGE = 5

def build_unpaid_orders_view(uid, page):
    offset = page * ORDERS_PER_PAGE

    conn = get_conn()
    cur = conn.cursor()

    # ===== COUNT ORDERS (IGNORE EMPTY + OWNED ITEMS) =====
    cur.execute(
        """
        SELECT COUNT(DISTINCT o.id)
        FROM orders o
        WHERE o.user_id=%s
          AND o.paid=0
          AND EXISTS (
              SELECT 1 FROM order_items oi
              WHERE oi.order_id = o.id
                AND NOT EXISTS (
                    SELECT 1 FROM user_movies um
                    WHERE um.user_id=%s
                      AND um.item_id=oi.item_id
                )
          )
        """,
        (uid, uid)
    )
    total = cur.fetchone()[0]

    # ===== IF NO UNPAID LEFT =====
    if total == 0:

        cur.close()
        conn.close()

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "🏘 Our Channel",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        )

        return (
            "📩<b>There are no unpaid orders.\n\nGo to our channel to buy Films</b>",
            kb
        )

    # ===== TOTAL BALANCE (IGNORE OWNED ITEMS) =====
    cur.execute(
        """
        SELECT COALESCE(SUM(o.amount), 0)
        FROM orders o
        WHERE o.user_id=%s
          AND o.paid=0
          AND EXISTS (
              SELECT 1 FROM order_items oi
              WHERE oi.order_id=o.id
                AND NOT EXISTS (
                    SELECT 1 FROM user_movies um
                    WHERE um.user_id=%s
                      AND um.item_id=oi.item_id
                )
          )
        """,
        (uid, uid)
    )
    total_amount = cur.fetchone()[0]

    # ===== FETCH ORDERS (OWNERSHIP SAFE) =====
    cur.execute(
        """
        SELECT
            o.id,
            COUNT(oi.item_id) AS items_count,
            o.amount AS amount,
            MAX(i.title) AS title,
            COUNT(DISTINCT i.group_key) AS gk_count,
            MIN(oi.price) AS base_price,
            MIN(i.group_key) AS group_key
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN items i ON i.id = oi.item_id
        WHERE o.user_id=%s
          AND o.paid=0
          AND NOT EXISTS (
              SELECT 1 FROM user_movies um
              WHERE um.user_id=%s
                AND um.item_id=oi.item_id
          )
        GROUP BY o.id
        ORDER BY o.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (uid, uid, ORDERS_PER_PAGE, offset)
    )
    rows = cur.fetchall()

    text = f"📩<b>Your unpaid orders ({total})</b>\n\n"
    kb = InlineKeyboardMarkup()

    for oid, count, amount, title, gk_count, base_price, group_key in rows:

        if count > 1 and gk_count == 1:
            name = f"{title} (EP {count})"
            show_amount = base_price
        else:
            if count == 1:
                name = title or "Single item"
            else:
                name = f"Group order ({count} items)"
            show_amount = amount

        short = name[:27] + "…" if len(name) > 27 else name
        text += f"• {short} — ₦{int(show_amount)}\n"

        kb.row(
            InlineKeyboardButton(
                f"❌ Remove {short}",
                callback_data=f"remove_unpaid:{oid}"
            )
        )

    text += f"\n<b>Total balance:</b> ₦{int(total_amount)}"

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "◀️ Back",
                callback_data=f"unpaid_prev:{page-1}"
            )
        )
    if offset + ORDERS_PER_PAGE < total:
        nav.append(
            InlineKeyboardButton(
                "Next ▶️",
                callback_data=f"unpaid_next:{page+1}"
            )
        )
    if nav:
        kb.row(*nav)

    kb.row(
        InlineKeyboardButton("💳 Pay all", callback_data="payall:"),
        InlineKeyboardButton("📩 Paid orders", callback_data="paid_orders")
    )

    kb.row(
        InlineKeyboardButton("🗑 Delete unpaid", callback_data="delete_unpaid")
    )

    kb.row(
        InlineKeyboardButton(
            "🏘 Our Channel",
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        )
    )

    cur.close()
    conn.close()
    return text, kb

def build_paid_orders_view(uid, page):
    offset = page * ORDERS_PER_PAGE

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id=%s AND paid=1",
        (uid,)
    )
    total = cur.fetchone()[0]

    if total == 0:
        cur.close()
        conn.close()
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🎥 PAID MOVIES", callback_data="my_movies"))
        kb.add(
            InlineKeyboardButton(
                "🏘 Our Channel",
                url=f"https://t.me/{CHANNEL.lstrip('@')}"
            )
        )
        return "📩 <b>There are no paid orders.\n\n Go to our Channel to buy films</b>", kb

    cur.execute(
        """
        SELECT
            o.id,
            COUNT(oi.item_id) AS items_count,
            MAX(i.title) AS title,
            COUNT(DISTINCT i.group_key) AS gk_count
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN items i ON i.id = oi.item_id
        WHERE o.user_id=%s AND o.paid=1
        GROUP BY o.id
        ORDER BY o.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (uid, ORDERS_PER_PAGE, offset)
    )
    rows = cur.fetchall()

    text = f"📩 <b>Your paid orders ({total})</b>\n\n"
    kb = InlineKeyboardMarkup()

    for oid, count, title, gk_count in rows:
        cur.execute(
            "SELECT COUNT(*) FROM user_movies WHERE order_id=%s AND user_id=%s",
            (oid, uid)
        )
        delivered = cur.fetchone()[0]

        remain = count - delivered

        if count > 1 and gk_count == 1:
            name = f"{title} (EP {count})"
        else:
            name = title or f"Group order ({count} items)"

        short = name[:27] + "…" if len(name) > 27 else name

        if remain > 0:
            text += f"• {short} — ✅ Paid (Remaining: {remain})\n"
        else:
            text += f"• {short} — ✅ Arrived\n"

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "◀️ Back",
                callback_data=f"paid_prev:{page-1}"
            )
        )
    if offset + ORDERS_PER_PAGE < total:
        nav.append(
            InlineKeyboardButton(
                "Next ▶️",
                callback_data=f"paid_next:{page+1}"
            )
        )
    if nav:
        kb.row(*nav)

    kb.add(InlineKeyboardButton("🎥PAID MOVIES", callback_data="my_movies"))
    kb.add(
        InlineKeyboardButton(
            "🏘Our Channel",
            url=f"https://t.me/{CHANNEL.lstrip('@')}"
        )
    )

    cur.close()
    conn.close()
    return text, kb



# ---------- START handler (VIEW) ----------
@bot.message_handler(commands=['start'])
def start_handler(msg):

    track_visited_user(msg)

    # 🛑 BAR BUYD DA GROUPITEM SU WUCE
    if msg.text.startswith("/start buyd_"):
        return
    if msg.text.startswith("/start groupitem_"):
        return
    # ===== ASALIN VIEW DINKA (BA A TABA SHI BA) =====
    args = msg.text.split()
    if len(args) > 1 and args[1] == "weakupdate":
        return send_weekly_list(msg)
    if len(args) > 1 and args[1] == "viewall":
        return send_weekly_list(msg)

    bot.send_message(msg.chat.id, "Welcome!")


# ========= BUYD (ITEM ONLY | DEEP LINK → DM) =========
from psycopg2.extras import RealDictCursor
import uuid
import time
import re

@bot.message_handler(func=lambda m: m.text and m.text.startswith("/start groupitem_"))
def groupitem_deeplink_handler(msg):
    uid = msg.from_user.id
    user_name = msg.from_user.first_name or "Customer"

    # ========= PARSE ITEM IDS + GROUP KEYS =========
    try:
        raw = msg.text.split("groupitem_", 1)[1]
        tokens = [x.strip() for x in re.split(r"[_,\s]+", raw) if x.strip()]
    except Exception:
        return

    if not tokens:
        return

    # ✅ SAFE CONNECTION
    conn = get_conn()
    if not conn:
        return
    cur = conn.cursor(cursor_factory=RealDictCursor)

    item_ids = []

    try:
        for token in tokens:
            # ==== IF ID ====
            if token.isdigit():
                item_ids.append(int(token))

            # ==== IF GROUP KEY ====
            else:
                cur.execute(
                    "SELECT id FROM items WHERE group_key=%s",
                    (token,)
                )
                rows = cur.fetchall()
                item_ids.extend([r["id"] for r in rows])

    except Exception:
        cur.close()
        conn.close()
        return

    if not item_ids:
        cur.close()
        conn.close()
        return

    # ========= FETCH ITEMS =========
    try:
        placeholders = ",".join(["%s"] * len(item_ids))
        cur.execute(
            f"""
            SELECT id, title, price, file_id, group_key
            FROM items
            WHERE id IN ({placeholders})
            """,
            tuple(item_ids)
        )
        items = cur.fetchall()
    except Exception:
        cur.close()
        conn.close()
        return

    if not items:
        cur.close()
        conn.close()
        return

    # ========= FILE_ID REQUIRED =========
    items = [i for i in items if i.get("file_id")]
    if not items:
        cur.close()
        conn.close()
        return

    item_ids_clean = [i["id"] for i in items]

    # ========= OWNERSHIP CHECK =========
    try:
        cur.execute(
            f"""
            SELECT 1 FROM user_movies
            WHERE user_id=%s
              AND item_id IN ({",".join(["%s"] * len(item_ids_clean))})
            LIMIT 1
            """,
            (uid, *item_ids_clean)
        )
        owned = cur.fetchone()
    except Exception:
        cur.close()
        conn.close()
        return

    if owned:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("📽 PAID MOVIES", callback_data="my_movies"))
        bot.send_message(
            uid,
            "✅ You have already purchased this movie.\n\n"
            "Please check your *Paid Movies* to download it again.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        cur.close()
        conn.close()
        return

    # ========= GROUP_KEY PRICING =========
    groups = {}
    for i in items:
        key = i["group_key"] or f"single_{i['id']}"
        if key not in groups:
            groups[key] = int(i["price"] or 0)

    total = sum(groups.values())
    item_count = len(items)

    if total <= 0:
        cur.close()
        conn.close()
        return

    # ========= REUSE / CREATE ORDER =========
    try:
        cur.execute(
            f"""
            SELECT o.id
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.user_id=%s
              AND o.paid=0
              AND oi.item_id IN ({",".join(["%s"] * len(item_ids_clean))})
            GROUP BY o.id
            HAVING COUNT(DISTINCT oi.item_id)=%s
            LIMIT 1
            """,
            (uid, *item_ids_clean, len(item_ids_clean))
        )
        row = cur.fetchone()
    except Exception:
        cur.close()
        conn.close()
        return

    if row:
        order_id = row["id"]
    else:
        order_id = str(uuid.uuid4())
        try:
            cur.execute(
                "INSERT INTO orders (id, user_id, amount, paid, type) VALUES (%s,%s,%s,0,'film')",
                (order_id, uid, total)
            )
            for i in items:
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, item_id, file_id, price)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (order_id, i["id"], i["file_id"], int(i["price"] or 0))
                )
            conn.commit()
        except Exception:
            conn.rollback()
            cur.close()
            conn.close()
            return

    # ========= FLUTTERWAVE (An sauya daga Paystack) =========
    display_title = f"{item_count} film(s)"
    # Mun kira sabon function din mu na Flutterwave
    pay_url = create_flutterwave_payment(uid, order_id, total, display_title)

    if not pay_url:
        bot.send_message(uid, "❌ Sorry, payment gateway is down. Try again later.")
        cur.close()
        conn.close()
        return

    # ========= FIXED TITLE DISPLAY =========
    unique_titles = [
        i["title"]
        for _, i in {
            (i["group_key"] or f"single_{i['id']}"): i
            for i in items
        }.items()
    ]

    # ========= FINAL UI =========
    kb = InlineKeyboardMarkup()

    # PAY NOW (TOP ROW)
    kb.add(
        InlineKeyboardButton("💳 PAY NOW", url=pay_url)
    )

    # SECOND ROW
    kb.row(
        InlineKeyboardButton("💵Pay with wallet", callback_data=f"walletpay:{order_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}")
    )

    sent = bot.send_message(
        uid,
        f"""🧺 <b>Your order created 🎉</b>

🎬 <b>You will buy:</b>
{", ".join(unique_titles)}

📦 Films: {item_count}
💵 Total amount: ₦{total}

👤 <b>Your name is:</b> {user_name}
🆔 <b>Order ID:</b>
<code>{order_id}</code>
""",
        parse_mode="HTML",
        reply_markup=kb
    )

    # ===== STORE MESSAGE FOR AUTO DELETE AFTER PAYMENT =====
    ORDER_MESSAGES[order_id] = (sent.chat.id, sent.message_id)

    cur.close()
    conn.close()


   


# ========= BUYD (ITEM ONLY | DEEP LINK → DM) =========

# ================= ADMIN MANUAL SUPPORT SYSTEM ===========

ADMIN_SUPPORT = {}

# ---------- /problem ----------
@bot.message_handler(commands=["problem"])
def admin_problem_cmd(m):
    if m.from_user.id != ADMIN_ID:
        return

    ADMIN_SUPPORT[m.from_user.id] = {"stage": "menu"}

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🔁 RESEND ORDER", callback_data="admin_resend"),
        InlineKeyboardButton("🎁 GIFT", callback_data="admin_gift")
    )

    bot.send_message(
        m.chat.id,
        "🧩 <b>ADMIN SUPPORT PANEL</b>\n\nZabi abin da kake so:",
        parse_mode="HTML",
        reply_markup=kb
    )


# ---------- RESEND ----------
@bot.callback_query_handler(func=lambda c: c.data == "admin_resend")
def admin_resend_start(c):
    if c.from_user.id != ADMIN_ID:
        return

    ADMIN_SUPPORT[c.from_user.id] = {"stage": "wait_order_id"}
    bot.answer_callback_query(c.id)
    bot.send_message(
        c.from_user.id,
        "🧾 Turo <b>ORDER ID</b>:",
        parse_mode="HTML"
    )


# ---------- GIFT ----------
@bot.callback_query_handler(func=lambda c: c.data == "admin_gift")
def admin_gift_start(c):
    if c.from_user.id != ADMIN_ID:
        return

    ADMIN_SUPPORT[c.from_user.id] = {"stage": "gift_user"}
    bot.answer_callback_query(c.id)
    bot.send_message(
        c.from_user.id,
        "👤 Turo <b>USER ID</b> wanda za a bawa kyauta:",
        parse_mode="HTML"
    )


# ---------- ADMIN FLOW ----------
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.from_user.id in ADMIN_SUPPORT)
def admin_support_flow(m):
    data = ADMIN_SUPPORT.get(m.from_user.id)
    if not data:
        return

    stage = data.get("stage")
    text = (m.text or "").strip()

    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        # ===== RESEND ORDER =====
        if stage == "wait_order_id":

            cur.execute(
                "SELECT user_id, amount, paid FROM orders WHERE id=%s",
                (text,)
            )
            row = cur.fetchone()

            if not row:
                ADMIN_SUPPORT.pop(m.from_user.id, None)
                bot.send_message(
                    m.chat.id,
                    "❌ <b>Order ID bai dace ba.</b>\nBabu wannan order a system.",
                    parse_mode="HTML"
                )
                return

            user_id, amount, paid = row

            if paid != 1:
                ADMIN_SUPPORT.pop(m.from_user.id, None)
                bot.send_message(
                    m.chat.id,
                    "⚠️ <b>ORDER BAI BIYA BA</b>\nFaɗa wa user ya kammala biya.",
                    parse_mode="HTML"
                )
                return

            cur.execute(
                "SELECT item_id FROM order_items WHERE order_id=%s",
                (text,)
            )
            items = cur.fetchall()

            if not items:
                ADMIN_SUPPORT.pop(m.from_user.id, None)
                bot.send_message(
                    m.chat.id,
                    "⚠️ Wannan order ɗin babu items a cikinsa.\nDuba order_items table."
                )
                return

            item_ids = [i[0] for i in items]

            ADMIN_SUPPORT[m.from_user.id] = {
                "stage": "resend_confirm",
                "user_id": user_id,
                "items": item_ids
            }

            bot.send_message(
                m.chat.id,
                f"""✅ <b>ORDER VERIFIED</b>

🆔 Order ID: <code>{text}</code>
👤 User ID: <code>{user_id}</code>
💰 Amount: ₦{amount}
🎬 Items: {len(item_ids)}

Tura <b>/sendall</b> domin a sake tura items.""",
                parse_mode="HTML"
            )
            return

        # ===== GIFT FLOW =====
        if stage == "gift_user":
            if not text.isdigit():
                bot.send_message(m.chat.id, "❌ Rubuta USER ID mai inganci.")
                return

            data["gift_user"] = int(text)
            data["stage"] = "gift_message"

            bot.send_message(
                m.chat.id,
                "✍️ Rubuta <b>MESSAGE</b> da user zai gani:",
                parse_mode="HTML"
            )
            return

        if stage == "gift_message":
            data["gift_message"] = text
            data["stage"] = "gift_item"

            bot.send_message(
                m.chat.id,
                "🎬 Rubuta <b>SUNAN ITEM</b> (title ko file name):",
                parse_mode="HTML"
            )
            return

        if stage == "gift_item":
            q = text.lower()

            cur.execute(
                """
                SELECT file_id, title
                FROM items
                WHERE LOWER(title) LIKE %s
                   OR LOWER(file_name) LIKE %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (f"%{q}%", f"%{q}%")
            )
            row = cur.fetchone()

            if not row:
                ADMIN_SUPPORT.pop(m.from_user.id, None)
                bot.send_message(
                    m.chat.id,
                    "❌ Ba a samu item a ITEMS table ba.",
                    parse_mode="HTML"
                )
                return

            file_id, title = row

            try:
                bot.send_video(
                    data["gift_user"],
                    file_id,
                    caption=data["gift_message"]
                )
            except:
                bot.send_document(
                    data["gift_user"],
                    file_id,
                    caption=data["gift_message"]
                )

            bot.send_message(
                m.chat.id,
                f"""🎁 <b>An kammala</b>

👤 User ID: <code>{data['gift_user']}</code>
🎬 Item: <b>{title}</b>""",
                parse_mode="HTML"
            )

            ADMIN_SUPPORT.pop(m.from_user.id, None)

    except Exception as e:
        print("ADMIN_SUPPORT_FLOW DB ERROR:", e)

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()




import uuid
import traceback
from psycopg2.extras import RealDictCursor

# ========= PAY ALL UNPAID (SAFE | GROUP-AWARE | CLEAN VERSION) =========
@bot.callback_query_handler(func=lambda c: c.data == "payall:")
def pay_all_unpaid(call):
    uid = call.from_user.id
    user_name = call.from_user.first_name or "Customer"
    bot.answer_callback_query(call.id)

    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ==================================================
        # 1️⃣ FETCH ALL UNPAID ORDER ITEMS
        # ==================================================
        cur.execute(
            """
            SELECT
                o.id        AS old_order_id,
                i.id        AS item_id,
                i.title,
                i.price,
                i.file_id,
                i.group_key
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN items i ON i.id = oi.item_id
            WHERE o.user_id=%s
              AND o.paid=0
            """,
            (uid,)
        )
        rows = cur.fetchall()

        if not rows:
            bot.send_message(uid, "❌ No unpaid orders found.")
            return

        # ==================================================
        # 2️⃣ REMOVE OWNED ITEMS
        # ==================================================
        all_item_ids = list({r["item_id"] for r in rows})

        if all_item_ids:
            cur.execute(
                f"""
                SELECT item_id
                FROM user_movies
                WHERE user_id=%s
                  AND item_id IN ({",".join(["%s"] * len(all_item_ids))})
                """,
                (uid, *all_item_ids)
            )
            owned_ids = {r["item_id"] for r in cur.fetchall()}
        else:
            owned_ids = set()

        if owned_ids:
            kb_owned = InlineKeyboardMarkup()
            kb_owned.add(
                InlineKeyboardButton("📽 PAID MOVIES", callback_data="my_movies")
            )

            bot.send_message(
                uid,
                "You have already purchased some of these movies.\n"
                "You can access them anytime from your paid movies section below.",
                reply_markup=kb_owned
            )

        items = [
            r for r in rows
            if r["file_id"]
            and int(r["price"] or 0) > 0
            and r["item_id"] not in owned_ids
        ]

        if not items:
            bot.send_message(uid, "❌ No payable items.")
            return

        item_ids = list({i["item_id"] for i in items})
        old_order_ids = list({i["old_order_id"] for i in items})

        # ==================================================
        # 3️⃣ GROUP KEY LOGIC
        # ==================================================
        groups = {}

        for i in items:
            key = i["group_key"] or f"single_{i['item_id']}"
            if key not in groups:
                groups[key] = {
                    "price": int(i["price"]),
                    "items": []
                }
            groups[key]["items"].append(i)

        total_amount = sum(g["price"] for g in groups.values())

        if total_amount <= 0:
            bot.send_message(uid, "❌ Invalid total amount.")
            return

        # ==================================================
        # 4️⃣ CREATE COLLECTOR ORDER
        # ==================================================
        order_id = str(uuid.uuid4())

        # Mun saka type='film' domin webhook ya gane
        cur.execute(
            """
            INSERT INTO orders (id, user_id, amount, paid, type)
            VALUES (%s, %s, %s, 0, 'film')
            """,
            (order_id, uid, total_amount)
        )

        for g in groups.values():
            for i in g["items"]:
                cur.execute(
                    """
                    INSERT INTO order_items
                    (order_id, item_id, file_id, price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (order_id, i["item_id"], i["file_id"], g["price"])
                )

        conn.commit()

        # ==================================================
        # 5️⃣ DELETE OLD ORDERS
        # ==================================================
        if old_order_ids:
            cur.execute(
                f"""
                DELETE FROM order_items
                WHERE order_id IN ({",".join(["%s"] * len(old_order_ids))})
                """,
                tuple(old_order_ids)
            )

            cur.execute(
                f"""
                DELETE FROM orders
                WHERE id IN ({",".join(["%s"] * len(old_order_ids))})
                """,
                tuple(old_order_ids)
            )

            conn.commit()

        # ==================================================
        # 6️⃣ FLUTTERWAVE (An sauya daga Paystack)
        # ==================================================
        pay_url = create_flutterwave_payment(
            uid,
            order_id,
            total_amount,
            "Pay All Unpaid Orders"
        )

        if not pay_url:
            bot.send_message(uid, "❌ Error generating payment link. Please try again.")
            return

        # ==================================================
        # 7️⃣ DISPLAY
        # ==================================================
        unique_titles = []
        seen = set()

        for key, g in groups.items():
            first_item = g["items"][0]
            title = first_item["title"]
            if key not in seen:
                unique_titles.append(title)
                seen.add(key)

        kb = InlineKeyboardMarkup()

        # PAY NOW
        kb.add(
            InlineKeyboardButton("💳 PAY NOW", url=pay_url)
        )

        # NEW WALLET BUTTON (LIKE GROUPITEM)
        kb.row(
            InlineKeyboardButton("💵Pay with wallet", callback_data=f"walletpay:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}")
        )

        sent = bot.send_message(
            uid,
            f"""🧺 <b>PAY ALL UNPAID ORDERS</b>

👤 <b>Your name is:</b> {user_name}

🎬 <b>Films:</b>
{", ".join(unique_titles)}

📦 <b>Films:</b> {len(item_ids)}
🗂 <b>G-orders:</b> {len(groups)}

💵 <b>Total amount:</b> ₦{total_amount}

🆔 <b>Order ID:</b>
<code>{order_id}</code>
""",
            parse_mode="HTML",
            reply_markup=kb
        )

        # ===== STORE MESSAGE FOR AUTO DELETE AFTER PAYMENT =====
        ORDER_MESSAGES[order_id] = (sent.chat.id, sent.message_id)

    except Exception:
        # Don kiyaye bot din daga tsayawa idan akwai error
        print(traceback.format_exc())
        pass

    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass


import uuid
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

series_sessions = {}

# ===============================
# COLLECT SERIES FILES (PRO EDIT VERSION)
# ===============================
@bot.message_handler(
    content_types=["video", "document"],
    func=lambda m: m.from_user.id in series_sessions
)
def series_collect_files(m):

    uid = m.from_user.id
    sess = series_sessions.get(uid)

    if not sess or sess.get("stage") != "collect":
        return

    try:
        # ================= GET FILE =================
        if m.video:
            dm_file_id = m.video.file_id
            file_name = m.video.file_name or "video.mp4"
        else:
            dm_file_id = m.document.file_id
            file_name = m.document.file_name or "file"

        # ================= SAVE =================
        sess["files"].append({
            "dm_file_id": dm_file_id,
            "file_name": file_name
        })

        total = len(sess["files"])

        # ================= CREATE OR EDIT MESSAGE =================
        if not sess.get("progress_msg_id"):

            msg = bot.send_message(
                uid,
                f"✅ An karɓi (1)\n📂 {file_name}"
            )
            sess["progress_msg_id"] = msg.message_id

        else:
            bot.edit_message_text(
                f"✅ An karɓi ({total})\n📂 {file_name}",
                uid,
                sess["progress_msg_id"]
            )

    except ApiTelegramException as e:
        bot.send_message(
            uid,
            f"❌ Telegram error:\n{str(e)}"
        )

    except Exception as e:
        bot.send_message(
            uid,
            f"❌ System error:\n{str(e)}"
        )


# ===============================
# OPTIONAL: CALL THIS WHEN DONE BUTTON IS PRESSED
# ===============================
def finish_series_collection(uid):

    sess = series_sessions.get(uid)
    if not sess:
        return

    total = len(sess.get("files", []))

    if total == 0:
        bot.send_message(uid, "⚠️ Babu file da aka karɓa.")
        return

    try:
        bot.edit_message_text(
            f"✅ An karɓi ({total})\n\n🎉 An karɓi dukkan files lafiya.",
            uid,
            sess.get("progress_msg_id")
        )
    except:
        bot.send_message(
            uid,
            f"✅ An karɓi ({total})\n🎉 An karɓi dukka lafiya."
        )


# ===============================
# DONE (CLEAN VERSION - NO LIST)
# ===============================
@bot.message_handler(
    func=lambda m: m.text and m.text.lower().strip() == "done" and m.from_user.id in series_sessions
)
def series_done(m):

    uid = m.from_user.id
    sess = series_sessions.get(uid)

    if not sess or sess.get("stage") != "collect":
        return

    files = sess.get("files", [])

    if not files:
        bot.send_message(uid, "❌ Babu fim da aka turo.")
        return

    total = len(files)

    # sunan fim na ƙarshe da aka karɓa
    last_name = files[-1]["file_name"]

    # ================= MESSAGE =================
    text = (
        f"✅ <b>An karɓi:</b> {last_name}\n"
        f"📦 <b>Adadi:</b> ({total})\n\n"
        f"❓ <b>Akwai Hausa series a ciki?</b>"
    )

    sess["stage"] = "ask_hausa"

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ EH", callback_data="hausa_yes"),
        InlineKeyboardButton("❌ A'A", callback_data="hausa_no")
    )

    bot.send_message(uid, text, parse_mode="HTML", reply_markup=kb)
# ===============================
# HAUSA CHOICE
# ===============================
@bot.callback_query_handler(
    func=lambda c: c.data in ["hausa_yes", "hausa_no"] and c.from_user.id in series_sessions
)
def handle_hausa_choice(c):
    uid = c.from_user.id
    sess = series_sessions.get(uid)
    bot.answer_callback_query(c.id)

    if c.data == "hausa_no":
        sess["hausa_matches"] = []
        sess["stage"] = "meta"
        bot.send_message(uid, "📸 Turo poster + caption (suna da farashi)")
        return

    sess["stage"] = "hausa_names"
    bot.send_message(uid, "✍️ Rubuta sunayen Hausa series (layi-layi)")

# ===============================
# RECEIVE HAUSA TITLES
# ===============================
@bot.message_handler(
    func=lambda m: m.text and m.from_user.id in series_sessions
    and series_sessions[m.from_user.id].get("stage") == "hausa_names"
)
def receive_hausa_titles(m):
    uid = m.from_user.id
    sess = series_sessions.get(uid)

    titles = [t.strip().lower() for t in m.text.split("\n") if t.strip()]
    matches = []

    for f in sess["files"]:
        fname = f["file_name"].lower()
        for t in titles:
            if t in fname:
                matches.append(f["file_name"])
                break

    sess["hausa_matches"] = matches
    sess["stage"] = "meta"

    bot.send_message(uid, "📸 Yanzu turo poster + caption (suna da farashi)")



# ===============================
# FINALIZE (UPLOAD + DB)
# ===============================
from telebot.apihelper import ApiTelegramException
import time
import uuid
from datetime import datetime

@bot.message_handler(
    content_types=["photo"],
    func=lambda m: m.from_user.id in series_sessions
)
def series_finalize(m):

    try:
        uid = m.from_user.id
        data = m.caption or ""
    except:
        return

    sess = series_sessions.get(uid)

    if sess.get("stage") != "meta":
        return

    # ================= PARSE CAPTION =================
    try:
        title, raw_price = data.strip().rsplit("\n", 1)
        has_comma = "," in raw_price
        price = int(raw_price.replace(",", "").strip())
    except:
        bot.send_message(uid, "❌ Caption bai dace ba.")
        return

    poster_file_id = m.photo[-1].file_id

    # ================= DB CONNECT =================
    try:
        conn = get_conn()
        cur = conn.cursor()
    except:
        return

    # ================= CREATE SERIES =================
    try:
        cur.execute(
            "INSERT INTO series (title, price, poster_file_id) VALUES (%s,%s,%s) RETURNING id",
            (title, price, poster_file_id)
        )
        series_id = cur.fetchone()[0]
    except:
        return

    item_ids = []
    created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    group_key = str(uuid.uuid4())
    total_files = len(sess["files"])

    # 🔥 ONE CLEAN MESSAGE
    progress_msg = bot.send_message(
        ADMIN_ID,
        f"⏳ Loading... (0/{total_files})"
    )

    # ================= SAFE SEND =================
    def safe_send_document(chat_id, file_id, caption):

        while True:
            try:
                return bot.send_document(chat_id, file_id, caption=caption)

            except ApiTelegramException as e:

                if e.error_code == 429:
                    retry = int(e.result_json["parameters"]["retry_after"])

                    bot.edit_message_text(
                        f"⏸ Rate limit hit.\nWaiting {retry}s...\n"
                        f"{len(item_ids)}/{total_files} saved",
                        ADMIN_ID,
                        progress_msg.message_id
                    )

                    time.sleep(retry)

                    bot.edit_message_text(
                        f"⏳ Loading... ({len(item_ids)}/{total_files})",
                        ADMIN_ID,
                        progress_msg.message_id
                    )

                    continue
                else:
                    return None

            except:
                return None

    # ================= UPLOAD LOOP =================
    for f in sess["files"]:

        msg = safe_send_document(
            STORAGE_CHANNEL,
            f["dm_file_id"],
            f["file_name"]
        )

        if not msg:
            continue

        doc = msg.document or msg.video
        if not doc:
            continue

        try:
            cur.execute(
                """
                INSERT INTO items
                (title, price, file_id, file_name, group_key,
                 created_at, channel_msg_id, channel_username)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    title,
                    price,
                    doc.file_id,
                    f["file_name"],
                    group_key,
                    created_at,
                    msg.message_id,
                    STORAGE_CHANNEL
                )
            )
            new_id = cur.fetchone()[0]
            item_ids.append(new_id)

        except:
            continue

        # Update progress cleanly
        bot.edit_message_text(
            f"⏳ Loading... ({len(item_ids)}/{total_files})",
            ADMIN_ID,
            progress_msg.message_id
        )

        time.sleep(1.1)

    # ================= COMMIT =================
    try:
        conn.commit()
    except:
        pass

    cur.close()
    conn.close()

    # ================= PUBLIC POST =================
    try:
        display_price = f"{price:,}" if has_comma else str(price)

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "🛒 Add to cart",
                callback_data=f"addcartdm:{group_key}"
            ),
            InlineKeyboardButton(
                "💳 Buy now",
                url=f"https://t.me/{BOT_USERNAME}?start=groupitem_{group_key}"
            )
        )

        bot.send_photo(
            CHANNEL,
            poster_file_id,
            caption=f"🎬 <b>{title}</b>\n💵Price: ₦{display_price}",
            parse_mode="HTML",
            reply_markup=kb
        )

    except:
        pass

    # Final message
    bot.edit_message_text(
        f"✅ Completed.\n{len(item_ids)}/{total_files} saved successfully.",
        ADMIN_ID,
        progress_msg.message_id
    )

    bot.send_message(uid, "🎉 Series an adana dukka lafiya.")
    del series_sessions[uid]


@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    try:
        uid = c.from_user.id
        data = c.data or ""
        user_name = c.from_user.first_name or "Customer"
    except:
        return

    


    from psycopg2.extras import RealDictCursor
    import uuid

    # ==================================================
    # CHECKOUT (CART)
    # ==================================================
    if data == "checkout":

        rows = get_cart(uid)

        if not rows:
            bot.answer_callback_query(c.id, "❌ Cart ɗinka babu komai.")
            return

        groups = {}
        total = 0

        for item_id, title, price, file_id, group_key in rows:

            if not file_id:
                continue

            p = int(price or 0)
            if p <= 0:
                continue

            key = group_key if group_key else f"single_{item_id}"

            if key not in groups:
                groups[key] = {
                    "price": p,
                    "items": []
                }

            groups[key]["items"].append((item_id, title, file_id))

        if not groups:
            bot.answer_callback_query(c.id, "❌ Babu item mai delivery a cart.")
            return

        # ==================================================
        # REMOVE OWNED MOVIES
        # ==================================================
        conn = None
        cur = None

        try:
            conn = get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            all_ids = []
            for g in groups.values():
                for item_id, _, _ in g["items"]:
                    all_ids.append(item_id)

            if all_ids:
                cur.execute(
                    f"""
                    SELECT item_id FROM user_movies
                    WHERE user_id=%s
                    AND item_id IN ({",".join(["%s"]*len(all_ids))})
                    """,
                    (uid, *all_ids)
                )

                owned_ids = {r["item_id"] for r in cur.fetchall()}
            else:
                owned_ids = set()

            if owned_ids:
                kb_owned = InlineKeyboardMarkup()
                kb_owned.add(
                    InlineKeyboardButton(
                        "📽 PAID MOVIES",
                        callback_data="my_movies"
                    )
                )

                bot.send_message(
                    uid,
                    "You have already purchased this movie.\n\nYou can view or download it again below 👇",
                    reply_markup=kb_owned
                )
                return

        except:
            return

        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except:
                pass

        # ==================================================
        # CALCULATE TOTAL
        # ==================================================
        for g in groups.values():
            total += g["price"]

        if total <= 0:
            bot.answer_callback_query(c.id, "❌ Farashi bai dace ba.")
            return

        order_id = str(uuid.uuid4())

        # ==================================================
        # CREATE ORDER
        # ==================================================
        conn = None
        cur = None

        try:
            conn = get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Mun kara type='film' domin Flutterwave Webhook ya gane
            cur.execute(
                "INSERT INTO orders (id,user_id,amount,paid,type) VALUES (%s,%s,%s,0,'film')",
                (order_id, uid, total)
            )

            for g in groups.values():
                for item_id, title, file_id in g["items"]:
                    cur.execute(
                        """
                        INSERT INTO order_items
                        (order_id,item_id,file_id,price)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (order_id, item_id, file_id, g["price"])
                    )

            conn.commit()

        except:
            if conn:
                conn.rollback()
            return

        finally:
            try:
                if cur:
                    cur.close()
                if conn:
                    conn.close()
            except:
                pass

        # ==================================================
        # CLEAR CART
        # ==================================================
        try:
            clear_cart(uid)
        except:
            pass

        # ==================================================
        # FLUTTERWAVE (An sauya daga Paystack)
        # ==================================================
        try:
            # An yi amfani da create_flutterwave_payment yadda ka bukata
            pay_url = create_flutterwave_payment(
                uid,
                order_id,
                total,
                "Cart Order"
            )
        except:
            return

        if not pay_url:
            return

        # ==================================================
        # FORMAT DISPLAY (LIKE PAYALL)
        # ==================================================
        unique_titles = []
        seen = set()

        for key, g in groups.items():
            first_item = g["items"][0]
            title = first_item[1]
            if key not in seen:
                unique_titles.append(title)
                seen.add(key)

        item_count = sum(len(g["items"]) for g in groups.values())

        kb = InlineKeyboardMarkup()

        # TOP ROW
        kb.add(
            InlineKeyboardButton("💳 PAY NOW", url=pay_url)
        )

        # SECOND ROW (NEW WALLET SYSTEM ADDED)
        kb.row(
            InlineKeyboardButton("💵Pay with wallet", callback_data=f"walletpay:{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}")
        )

        sent = bot.send_message(
            uid,
            f"""🧺 <b>CART CHECKOUT</b>

👤 <b>Your name is:</b> {user_name}

🎬 <b>Films:</b>
{", ".join(unique_titles)}

📦 <b>Films:</b> {item_count}
🗂 <b>G-orders:</b> {len(groups)}

💵 <b>Total amount:</b> ₦{total}

🆔 <b>Order ID:</b>
<code>{order_id}</code>
""",
            parse_mode="HTML",
            reply_markup=kb
        )

        # ===== NEW: STORE MESSAGE FOR WEBHOOK AUTO DELETE =====
        ORDER_MESSAGES[order_id] = (sent.chat.id, sent.message_id)

        bot.answer_callback_query(c.id)
        return




    

# =====================
    # VIEW CART
    # =====================
    if data == "viewcart":

        try:
            text, kb = build_cart_view(uid)

        except Exception as e:
            bot.send_message(
                uid,
                f"❌ ERROR inside build_cart_view:\n<code>{str(e)}</code>",
                parse_mode="HTML"
            )
            bot.answer_callback_query(c.id, "❌ build_cart_view error")
            return

        try:
            msg = bot.send_message(
                uid,
                text,
                reply_markup=kb,
                parse_mode="HTML"
            )

            cart_sessions[uid] = msg.message_id

        except Exception as e:
            bot.send_message(
                uid,
                f"❌ ERROR sending cart message:\n<code>{str(e)}</code>",
                parse_mode="HTML"
            )
            bot.answer_callback_query(c.id, "❌ Send message failed")
            return

        bot.answer_callback_query(c.id)
        return

    # ================= FEEDBACK =================
    if data.startswith("feedback:"):

        try:
            bot.answer_callback_query(c.id)
            parts = data.split(":", 2)
            if len(parts) != 3:
                bot.answer_callback_query(
                    c.id,
                    "⚠️ Invalid feedback data",
                    show_alert=True
                )
                return

            mood, order_id = parts[1], parts[2]

            conn = get_conn()              # ✅ GYARA KADAI
            cur = conn.cursor()

            cur.execute(
                """
                SELECT paid
                FROM orders
                WHERE id=%s AND user_id=%s
                """,
                (order_id, uid)
            )
            row = cur.fetchone()

            if not row or row[0] != 1:
                cur.close()
                conn.close()               # ✅ GYARA KADAI
                bot.answer_callback_query(
                    c.id,
                    "⚠️ Wannan order ba naka bane ko ba'a biya ba.",
                    show_alert=True
                )
                return

            cur.execute(
                "SELECT 1 FROM feedbacks WHERE order_id=%s",
                (order_id,)
            )
            if cur.fetchone():
                cur.close()
                conn.close()               # ✅ GYARA KADAI
                bot.answer_callback_query(
                    c.id,
                    "Ka riga ka bada ra'ayi.",
                    show_alert=True
                )
                return

            cur.execute(
                """
                INSERT INTO feedbacks (order_id, user_id, mood)
                VALUES (%s, %s, %s)
                """,
                (order_id, uid, mood)
            )
            conn.commit()
            cur.close()
            conn.close()                   # ✅ GYARA KADAI

        except Exception:
            try:
                cur.close()
                conn.close()               # ✅ GYARA KADAI
            except:
                pass
            bot.answer_callback_query(
                c.id,
                "⚠️ Ba a iya adana ra'ayi ba",
                show_alert=True
            )
            return

        try:
            chat = bot.get_chat(uid)
            fname = chat.first_name or "User"
        except:
            fname = "User"

        admin_messages = {
            "very": "😘 Gaskiya na ji daɗin siyayya da bot ɗinku, yana da sauki kuma wannan babban cigabane",
            "good": "🙂 Na ji daɗin siyayya kuma gaskiya wannan bot ba karimin sauki yakawo manaba",
            "neutral": "😓 Ban gama fahimta sosai ba, ku karayin vidoe don wayar mana da kai",
            "angry": "🤬 Wannan bot naku bai kyauta min ba, yakamata ku gyara tsarin kasuwancinku domin akwai matsala"
        }

        admin_text = (
            "📣 FEEDBACK RECEIVED\n\n"
            f"👤 User: {fname}\n"
            f"🆔 ID: {uid}\n"
            f"📦 Order: {order_id}\n"
            f"💬 Mood: {mood}\n\n"
            f"{admin_messages.get(mood, mood)}"
        )

        try:
            bot.send_message(ADMIN_ID, admin_text)
        except:
            pass

        try:
            bot.edit_message_reply_markup(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                reply_markup=None
            )
        except:
            pass

        bot.send_message(
            uid,
            "🙏 Mun gode da ra'ayinka! Za mu yi aiki da shi Insha Allah."
        )
        return



    # =====================
    # GROUPITEM START
    # =====================
    if data == "groupitems":
        if uid != ADMIN_ID:
            bot.answer_callback_query(c.id, "Ba izini.")
            return

        series_sessions[uid] = {
            "files": [],
            "stage": "collect"
        }

        bot.send_message(
            uid,
            "📺 <b>Series Mode ya fara</b>\n\n"
            "Ka fara turo videos/documents.\n"
            "Idan ka gama rubuta <b>Done</b>.",
            parse_mode="HTML"
        )
        return

 

    # =====================
    # ADD TO CART (PRO | IDS + GROUP KEYS)
    # =====================
    if data.startswith("addcartdm:"):
        try:
            raw = data.split(":", 1)[1]
            parts = raw.replace("|", "_").split("_")
        except:
            bot.answer_callback_query(c.id, "❌ Invalid item")
            return

        if not parts:
            bot.answer_callback_query(c.id, "❌ Invalid item")
            return

        added = 0
        skipped = 0
        owned = 0   # ✅ NEW

        try:
            conn = get_conn()
            cur = conn.cursor()

            for part in parts:

                # =====================
                # IF NUMERIC → ITEM ID
                # =====================
                if part.isdigit():

                    cur.execute(
                        "SELECT id FROM items WHERE id=%s",
                        (part,)
                    )
                    if not cur.fetchone():
                        skipped += 1
                        continue

                    # ✅ CHECK IF USER ALREADY OWNS ITEM
                    cur.execute(
                        """
                        SELECT 1 FROM order_items oi
                        JOIN orders o ON o.id = oi.order_id
                        WHERE o.user_id=%s AND oi.item_id=%s AND o.paid=1
                        """,
                        (uid, part)
                    )
                    if cur.fetchone():
                        owned += 1
                        continue

                    cur.execute(
                        "SELECT 1 FROM cart WHERE user_id=%s AND item_id=%s",
                        (uid, part)
                    )
                    if cur.fetchone():
                        skipped += 1
                        continue

                    cur.execute(
                        "INSERT INTO cart (user_id, item_id) VALUES (%s, %s)",
                        (uid, part)
                    )
                    added += 1

                # =====================
                # OTHERWISE → GROUP KEY
                # =====================
                else:

                    cur.execute(
                        "SELECT id FROM items WHERE group_key=%s",
                        (part,)
                    )
                    group_items = cur.fetchall()

                    if not group_items:
                        skipped += 1
                        continue

                    for row in group_items:
                        item_id = row[0]

                        # ✅ CHECK IF USER ALREADY OWNS ITEM
                        cur.execute(
                            """
                            SELECT 1 FROM order_items oi
                            JOIN orders o ON o.id = oi.order_id
                            WHERE o.user_id=%s AND oi.item_id=%s AND o.paid=1
                            """,
                            (uid, item_id)
                        )
                        if cur.fetchone():
                            owned += 1
                            continue

                        cur.execute(
                            "SELECT 1 FROM cart WHERE user_id=%s AND item_id=%s",
                            (uid, item_id)
                        )
                        if cur.fetchone():
                            skipped += 1
                            continue

                        cur.execute(
                            "INSERT INTO cart (user_id, item_id) VALUES (%s, %s)",
                            (uid, item_id)
                        )
                        added += 1

            conn.commit()

        except Exception:
            conn.rollback()
            bot.answer_callback_query(c.id, "❌ Add to cart failed")
            return

        # ===== USER FEEDBACK =====
        if owned:
            bot.answer_callback_query(
                c.id,
                "🎬 You already purchased this film."
            )
        elif added and skipped:
            bot.answer_callback_query(
                c.id,
                f"✅ Added {added} | ⚠️ Skipped {skipped}"
            )
        elif added:
            bot.answer_callback_query(
                c.id,
                "✅ Item(s) added to cart"
            )
        else:
            bot.answer_callback_query(
                c.id,
                "⚠️ Already in cart"
            )

        return


    
    
       

    # =====================
    # REMOVE FROM CART
    # =====================
    if data.startswith("removecart:"):
        raw = data.split(":", 1)[1]

        removed = 0

        try:
            conn = get_conn()
            cur = conn.cursor()

            parts = [p.strip() for p in raw.split("_") if p.strip()]
            ids = set()

            for part in parts:

                # ===== ID =====
                if part.isdigit():
                    ids.add(int(part))

                # ===== GROUP KEY =====
                else:
                    cur.execute(
                        "SELECT id FROM items WHERE group_key=%s",
                        (part,)
                    )
                    rows = cur.fetchall()
                    for r in rows:
                        ids.add(r[0])

            if not ids:
                bot.answer_callback_query(c.id, "❌ No item selected")
                return

            for item_id in ids:
                cur.execute(
                    "DELETE FROM cart WHERE user_id=%s AND item_id=%s",
                    (uid, item_id)
                )
                removed += cur.rowcount

            conn.commit()
            cur.close()
            conn.close()

        except Exception:
            try:
                conn.rollback()
                cur.close()
                conn.close()
            except:
                pass

            bot.answer_callback_query(c.id, "❌ Remove failed")
            return

        # 🚫 idan babu abin da aka goge
        if removed == 0:
            bot.answer_callback_query(
                c.id,
                "⚠️ Wannan item din baya cikin cart"
            )
            return

        # 🔁 EDIT CART MESSAGE (FIXED)
        text, kb = build_cart_view(uid)
        try:
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            print("EDIT FAILED:", e)

        bot.answer_callback_query(c.id, "🗑 Item removed")
        return

    # =====================
    # CLEAR CART
    # =====================
    if data == "clearcart":
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM cart WHERE user_id=%s",
                (uid,)
            )
            removed = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
        except Exception:
            try:
                conn.rollback()
                cur.close()
                conn.close()
            except:
                pass

            bot.answer_callback_query(c.id, "❌ Clear failed")
            return

        if removed == 0:
            bot.answer_callback_query(
                c.id,
                "⚠️ Cart dinka tuni babu komai"
            )
            return

        # 🔁 EDIT CART MESSAGE (FIXED)
        text, kb = build_cart_view(uid)
        try:
            bot.edit_message_text(
                chat_id=c.message.chat.id,
                message_id=c.message.message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            print("EDIT FAILED:", e)

        bot.answer_callback_query(c.id, "🧹 Cart cleared")
        return

    # =====================
    # PENDING / UNPAID ORDERS
    # =====================
    if data == "myorders_new":
        text, kb = build_unpaid_orders_view(uid, page=0)

        bot.send_message(
            chat_id=uid,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        bot.answer_callback_query(c.id)
        return


    # ================= MY MOVIES =================
    if data == "my_movies":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                "🔍 Check movie",
                callback_data="_resend_search_"
            )
        )

        bot.edit_message_text(
            chat_id=c.message.chat.id,
            message_id=c.message.message_id,
            text=(
                "🎥 <b>PAID MOVIES</b>\n"
                "Your previously purchased movies will be resent to you.\n\n"
                "🔍 Tap the button below to search your purchased movies."
            ),
            parse_mode="HTML",
            reply_markup=kb
        )

        bot.answer_callback_query(c.id)
        return


    # ================= 🔍 RESEND SEARCH (STATE SETTER) =================
    if data == "_resend_search_":
        user_states[uid] = {"action": "_resend_search_"}

        bot.send_message(
            uid,
            "🔍 <b>Checking Mode</b>\n"
            "Type the movie name or first letter(s).\n"
            "Example: <b>Dan</b> = Dan Tawaye",
            parse_mode="HTML"
        )

        bot.answer_callback_query(c.id)
        return



# ================= RESEND BY DAYS =================
    if data.startswith("resend:"):
        try:
            days = int(data.split(":", 1)[1])
        except:
            bot.answer_callback_query(c.id, "❌ Invalid time.")
            return

        try:
            conn = get_conn()
            used = conn.execute(
                "SELECT COUNT(*) FROM resend_logs WHERE user_id=%s",
                (uid,)
            ).fetchone()[0]
        except:
            bot.answer_callback_query(c.id, "❌ Database error.")
            return

        if used >= 10:
            bot.send_message(
                uid,
                "⚠️ You’ve reached the maximum resend limit (10 times).\n"
                "Please purchase the movie again."
            )
            bot.answer_callback_query(c.id)
            return

        try:
            conn = get_conn()
            rows = conn.execute(
                """
                SELECT DISTINCT ui.item_id, i.file_id, i.title
                FROM user_movies ui
                JOIN items i ON i.id = ui.item_id
                WHERE ui.user_id=%s
                  AND ui.created_at >= NOW() - INTERVAL '%s days'
                ORDER BY ui.created_at ASC
                """,
                (uid, days)
            ).fetchall()
        except:
            bot.answer_callback_query(c.id, "❌ Database error.")
            return

        if not rows:
            bot.send_message(uid, "❌ Babu fim a wannan lokacin.")
            bot.answer_callback_query(c.id)
            return

        for _, file_id, title in rows:
            try:
                bot.send_video(uid, file_id, caption=f"🎬 {title}")
            except:
                bot.send_document(uid, file_id, caption=f"🎬 {title}")

        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO resend_logs (user_id, used_at) VALUES (%s, NOW())",
                (uid,)
            )
            conn.commit()
        except:
            pass

        bot.send_message(
            uid,
            f"✅ Movies resent successfully ({len(rows)}).\n"
            "⚠️ Limit: 10 times only."
        )
        bot.answer_callback_query(c.id)
        return


    # ================= RESEND ONE ITEM =================
    if data.startswith("resend_one:"):
        try:
            item_id = int(data.split(":", 1)[1])
        except:
            bot.answer_callback_query(c.id, "❌ Invalid movie.")
            return

        try:
            conn = get_conn()
            used = conn.execute(
                "SELECT COUNT(*) FROM resend_logs WHERE user_id=%s",
                (uid,)
            ).fetchone()[0]
        except:
            bot.answer_callback_query(c.id, "❌ Database error.")
            return

        if used >= 10:
            bot.send_message(
                uid,
                "⚠️ You’ve reached the maximum resend limit (10 times)."
            )
            bot.answer_callback_query(c.id)
            return

        try:
            conn = get_conn()
            row = conn.execute(
                """
                SELECT i.file_id, i.title
                FROM user_movies ui
                JOIN items i ON i.id = ui.item_id
                WHERE ui.user_id=%s AND ui.item_id=%s
                LIMIT 1
                """,
                (uid, item_id)
            ).fetchone()
        except:
            bot.answer_callback_query(c.id, "❌ Database error.")
            return

        if not row:
            bot.answer_callback_query(c.id, "❌ Movie not found.")
            return

        file_id, title = row

        try:
            bot.send_video(uid, file_id, caption=f"🎬 {title}")
        except:
            bot.send_document(uid, file_id, caption=f"🎬 {title}")

        try:
            conn = get_conn()
            conn.execute(
                "INSERT INTO resend_logs (user_id, used_at) VALUES (%s, NOW())",
                (uid,)
            )
            conn.commit()
        except:
            pass

        bot.answer_callback_query(
            c.id,
            "✅ Movie resent successfully.\n⚠️ Limit: 10 times."
        )
        return



   

     # ================= START SERIES MODE =================
    if data == "start_series":
        series_sessions[uid] = {
            "stage": "collect",
            "files": [],
            "hausa_titles": [],
            "hausa_matches": []
        }

        bot.answer_callback_query(c.id)
        bot.send_message(
            uid,
            "📦 <b>Series mode ya fara</b>\n\n"
            "➡️ Turo dukkan fina-finai (video ko document)\n"
            "➡️ Idan ka gama, rubuta <b>done</b>",
            parse_mode="HTML"
        )
        return



   

    # =====================
    # UNPAID PAGINATION
    # =====================
    if data.startswith("unpaid_next:") or data.startswith("unpaid_prev:"):
        page = int(data.split(":")[1])
        text, kb = build_unpaid_orders_view(uid, page)
        bot.edit_message_text(
            chat_id=uid,
            message_id=c.message.message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        return



# =====================
    # REMOVE SINGLE UNPAID
    # =====================
    if data.startswith("remove_unpaid:"):
        oid = data.split(":", 1)[1]

        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT 1 FROM orders
                WHERE id=%s AND user_id=%s AND paid=0
                """,
                (oid, uid)
            )
            if not cur.fetchone():
                bot.answer_callback_query(c.id, "❌ Order not found")
                cur.close()
                return

            cur.execute(
                "DELETE FROM order_items WHERE order_id=%s",
                (oid,)
            )

            cur.execute(
                "DELETE FROM orders WHERE id=%s",
                (oid,)
            )

            conn.commit()
            cur.close()

        except Exception:
            try:
                conn.rollback()
            except:
                pass
            bot.answer_callback_query(c.id, "❌ Failed to remove")
            return

        text, kb = build_unpaid_orders_view(uid, page=0)
        bot.edit_message_text(
            chat_id=uid,
            message_id=c.message.message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        bot.answer_callback_query(c.id, "❌ Order removed")
        return

    # =====================
    # DELETE ALL UNPAID
    # =====================
    if data == "delete_unpaid":
        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute(
                """
                DELETE FROM order_items
                WHERE order_id IN (
                    SELECT id FROM orders
                    WHERE user_id=%s AND paid=0
                )
                """,
                (uid,)
            )

            cur.execute(
                """
                DELETE FROM orders
                WHERE user_id=%s AND paid=0
                """,
                (uid,)
            )

            conn.commit()
            cur.close()

        except Exception:
            try:
                conn.rollback()
            except:
                pass
            bot.answer_callback_query(c.id, "❌ Failed to delete")
            return

        text, kb = build_unpaid_orders_view(uid, page=0)
        bot.edit_message_text(
            chat_id=uid,
            message_id=c.message.message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        bot.answer_callback_query(c.id, "🗑 All unpaid orders deleted")
        return    
    

  
    # =====================
    # OPEN PAID ORDERS
    # =====================
    if data == "paid_orders":
        text, kb = build_paid_orders_view(uid, page=0)

        bot.send_message(
            chat_id=uid,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

        bot.answer_callback_query(c.id)
        return




    # =====================
    # ALL FILMS PAGINATION
    # =====================
    if data == "allfilms_prev":
        sess = allfilms_sessions.get(uid)
        if not sess:
            return

        idx = sess["index"] - 1
        if idx >= 0:
            send_allfilms_page(uid, idx)
        return



    # ================= FEEDBACK =================
    if not data.startswith("feedback:"):
        return   # ❗️MUHIMMI: kada a answer a nan

    parts = data.split(":", 2)
    if len(parts) != 3:
        print("❌ INVALID CALLBACK FORMAT:", data)
        bot.answer_callback_query(
            c.id,
            "⚠️ Invalid feedback data",
            show_alert=True
        )
        return

    mood, order_id = parts[1], parts[2]

    print("🧠 FEEDBACK MOOD:", mood)
    print("📦 FEEDBACK ORDER_ID:", order_id)

    # ================= CHECK ORDER =================
    try:
        row = conn.execute(
            """
            SELECT id FROM orders
            WHERE id=%s AND user_id=%s AND paid=1
            """,
            (order_id, uid)
        ).fetchone()
    except Exception as e:
        print("❌ DB ERROR (ORDER CHECK):", e)
        bot.answer_callback_query(
            c.id,
            "⚠️ Database error",
            show_alert=True
        )
        return

    print("📄 ORDER ROW:", row)

    if not row:
        bot.answer_callback_query(
            c.id,
            "⚠️ Wannan order ba naka bane ko ba'a biya ba.",
            show_alert=True
        )
        return

    # ================= CHECK DUPLICATE =================
    exists = conn.execute(
        "SELECT 1 FROM feedbacks WHERE order_id=%s",
        (order_id,)
    ).fetchone()

    print("🧾 FEEDBACK EXISTS:", exists)

    if exists:
        bot.answer_callback_query(
            c.id,
            "Ka riga ka bada ra'ayi.",
            show_alert=True
        )
        return

    # ================= INSERT FEEDBACK =================
    try:
        conn.execute(
            """
            INSERT INTO feedbacks (order_id, user_id, mood)
            VALUES (%s, %s, %s)
            """,
            (order_id, uid, mood)
        )
        conn.commit()
    except Exception as e:
        print("❌ INSERT FEEDBACK ERROR:", e)
        bot.answer_callback_query(
            c.id,
            "⚠️ Ba a iya adana ra'ayi ba",
            show_alert=True
        )
        return

    print("✅ FEEDBACK SAVED SUCCESSFULLY")

    # ================= USER INFO =================
    try:
        chat = bot.get_chat(uid)
        fname = chat.first_name or "User"
    except Exception as e:
        print("⚠️ GET_CHAT ERROR:", e)
        fname = "User"

    admin_messages = {
        "very": "😘 Gaskiya na ji daɗin siyayya da bot ɗinku",
        "good": "🙂 Na ji daɗin siyayya",
        "neutral": "😓 Ban gama fahimta sosai ba",
        "angry": "🤬 Wannan bot yana bani ciwon kai"
    }

    admin_text = (
        "📣 FEEDBACK RECEIVED\n\n"
        f"👤 User: {fname}\n"
        f"🆔 ID: {uid}\n"
        f"📦 Order: {order_id}\n"
        f"💬 Mood: {mood}\n\n"
        f"{admin_messages.get(mood, mood)}"
    )

    # ================= SEND TO ADMIN =================
    try:
        bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        print("⚠️ ADMIN SEND ERROR:", e)

    # ================= REMOVE BUTTONS =================
    try:
        bot.edit_message_reply_markup(
            chat_id=c.message.chat.id,
            message_id=c.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        print("⚠️ REMOVE BUTTON ERROR:", e)

    # ================= USER CONFIRM =================
    bot.answer_callback_query(c.id)
    bot.send_message(
        uid,
        "🙏 Mun gode da ra'ayinka! Za mu yi aiki da shi Insha Allah."
    )    
    # =====================
    # ADD MOVIE (ADMIN)
    # =====================
    if data == "addmovie":
        if uid != ADMIN_ID:
            bot.answer_callback_query(c.id, "Only admin.")
            return
        admin_states[uid] = {"state": "add_movie_wait_file"}
        bot.send_message(uid, "Turo film.")
        bot.answer_callback_query(c.id)
        return

    # =====================
    # WEEKLY BUY
    # =====================
    if data.startswith("weekly_buy:"):
        try:
            idx = int(data.split(":", 1)[1])
        except:
            bot.answer_callback_query(c.id, "Invalid.")
            return

        row = conn.execute(
            "SELECT items FROM weekly ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not row:
            bot.answer_callback_query(c.id, "No weekly items.")
            return

        items = json.loads(row[0] or "[]")

        if idx < 0 or idx >= len(items):
            bot.answer_callback_query(c.id, "Invalid item.")
            return

        item = items[idx]

        title = item["title"]
        price = int(item["price"])

        remaining_price, applied_sum, applied_ids = apply_credits_to_amount(
            uid,
            price
        )

        order_id = create_single_order_for_weekly(
            uid,
            title,
            remaining_price
        )

        bot.send_message(
            uid,
            f"Oda {order_id} – ₦{remaining_price}"
        )
        bot.answer_callback_query(c.id)
        return    
    # ======================================================
    # ================= ALL FILMS OPEN =====================
    # ======================================================
    if data == "all_films":
        rows = build_allfilms_rows()
        if not rows:
            bot.answer_callback_query(c.id, "❌ Babu fim a DB")
            return

        pages = paginate(rows, PER_PAGE)

        allfilms_sessions[uid] = {
            "pages": pages,
            "index": 0,
            "last_msg": c.message.message_id
        }

        send_allfilms_page(uid, 0)
        bot.answer_callback_query(c.id)
        return

    # ======================================================
    # ================= ALL FILMS NEXT =====================
    # ======================================================
    if data == "allfilms_next":
        sess = allfilms_sessions.get(uid)
        if not sess:
            bot.answer_callback_query(c.id)
            return

        send_allfilms_page(uid, sess["index"] + 1)
        bot.answer_callback_query(c.id)
        return

    # ======================================================
    # ================= ALL FILMS PREV =====================
    # ======================================================
    if data == "allfilms_prev":
        sess = allfilms_sessions.get(uid)
        if not sess:
            bot.answer_callback_query(c.id)
            return

        send_allfilms_page(uid, sess["index"] - 1)
        bot.answer_callback_query(c.id)
        return


 # Map new erase_all_data callback to existing erase_data handler (compat shim)
    if data == "erase_all_data":
        data = "erase_data"



    # NEW WEAK UPDATE SYSTEM
    if data == "weak_update":
        start_weak_update(msg=c.message)
        return

    # checkjoin: after user clicks I've Joined
    if data == "checkjoin":
        try:
            if check_join(uid):
                bot.answer_callback_query(
                    callback_query_id=c.id,
                    text=tr_user(uid, "joined_ok", default="✔ Channel joined!")
                )

                bot.send_message(
                    uid,
                    "Shagon Algaita Movie Store na kawo maka zaɓaɓɓun fina-finai masu inganci. "
                    "Mun tace su tsaf daga ɗanyen kaya, mun ware mafi kyau kawai. "
                    "Duk fim ɗin da ka siya a nan, tabbas ba za mu ba ka kunya ba.",
                    reply_markup=user_main_menu(uid)
                )

                bot.send_message(
                    uid,
                    "Sannu da zuwa!\n Duk fim din da kakeso ka shiga channel dinmu ka duba shi?:",
                    reply_markup=reply_menu(uid)
                )

            else:
                bot.answer_callback_query(
                    callback_query_id=c.id,
                    text=tr_user(uid, "not_joined", default="❌ You are not logged in.")
                )

        except Exception as e:
            print("checkjoin callback error:", e)

        return

 
  

    

# go home
    if data == "go_home":
        try:
            bot.answer_callback_query(callback_query_id=c.id)
            bot.send_message(
                uid,
                "Sannu! Ga zabuka, domin fara wa:",
                reply_markup=reply_menu(uid)
            )
        except Exception as e:
            print("go_home error:", e)
        return
    



    # Support Help -> Open admin DM directly (NO messages to admin, NO notifications)
    if data == "support_help":
        try:
            bot.answer_callback_query(callback_query_id=c.id)
        except:
            pass

        if ADMIN_USERNAME:
            # Open admin DM directly
            bot.send_message(uid, f"👉 Tuntuɓi admin kai tsaye: https://t.me/{ADMIN_USERNAME}")
        else:
            bot.send_message(uid, "Admin username bai sa ba. Tuntubi support.")
        return


    # fallback
    try:
        bot.answer_callback_query(callback_query_id=c.id)
    except:
        pass


# ========== /myorders command (SAFE – ITEMS BASED | POSTGRES) ==========
@bot.message_handler(commands=["myorders"])
def myorders(message):
    uid = message.from_user.id

    conn = None
    cur = None

    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, amount, paid
            FROM orders
            WHERE user_id=%s
            ORDER BY created_at DESC
            """,
            (uid,)
        )
        rows = cur.fetchall()

        if not rows:
            bot.reply_to(
                message,
                "❌ You don’t have any orders yet.",
                reply_markup=reply_menu(uid)
            )
            return

        txt = "🛒 <b>Your Orders</b>\n\n"

        for oid, amount, paid in rows:
            amount = int(amount or 0)

            # 🔒 SAFE COUNT (order_items ONLY)
            cur.execute(
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE order_id=%s
                """,
                (oid,)
            )
            info = cur.fetchone()
            items_count = info[0] if info else 0

            # 🛡 KARIYA: idan babu item kwata-kwata, tsallake
            if items_count <= 0:
                continue

            # 🏷 LABEL
            label = "1 item" if items_count == 1 else f"Group items ({items_count})"

            txt += (
                f"🆔 <code>{oid}</code>\n"
                f"📦 {label}\n"
                f"💰 Amount: ₦{amount}\n"
                f"💳 Status: {'✅ Paid' if paid else '❌ Unpaid'}\n\n"
            )

        bot.send_message(
            uid,
            txt,
            parse_mode="HTML",
            reply_markup=reply_menu(uid)
        )

    except Exception as e:
        print("MYORDERS DB ERROR:", e)
        bot.reply_to(
            message,
            "⚠️ An samu matsala. Sake gwadawa daga baya.",
            reply_markup=reply_menu(uid)
        )

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
#s ========== ADMIN FILE UPLOAD (ITEMS ONLY

# ================== SALES REPORT SYSTEM (ITEMS BASED – POSTGRES FIXED) ==================

import threading
import time
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor


# ================= TIME =================
def _ng_now():
    return datetime.utcnow() + timedelta(hours=1)

def _last_day_of_month(dt):
    nxt = dt.replace(day=28) + timedelta(days=4)
    return (nxt - timedelta(days=nxt.day)).day


# ================= ONE REPORT ENGINE =================
def send_sales_report(since_dt, title, target_chat_id, silent_if_empty=False):

    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            """
            WITH grouped_orders AS (
                SELECT
                    o.id AS order_id,
                    COALESCE(i.group_key, 'single_' || i.id) AS grp,
                    MIN(i.title) AS title,
                    MAX(oi.price) AS group_price
                FROM orders o
                JOIN order_items oi ON oi.order_id = o.id
                JOIN items i ON i.id = oi.item_id
                WHERE o.paid = 1
                  AND o.created_at >= %s
                GROUP BY o.id, grp
            )
            SELECT
                grp,
                MIN(title) AS title,
                COUNT(order_id) AS orders,
                SUM(group_price) AS total
            FROM grouped_orders
            GROUP BY grp
            ORDER BY total DESC
            """,
            (since_dt,)
        )

        rows = cur.fetchall()

    except Exception as e:
        bot.send_message(
            target_chat_id,
            f"❌ Sales report DB error:\n{e}"
        )
        return

    finally:
        cur.close()
        conn.close()

    # ===== NO SALES =====
    if not rows:
        if not silent_if_empty:
            bot.send_message(
                target_chat_id,
                f"{title}\n\n❌ No sales yet."
            )
        return

    msg = f"{title}\n\n"
    total_orders = 0
    grand_total = 0

    for r in rows:
        qty = r["orders"]
        amount = int(r["total"] or 0)

        total_orders += qty
        grand_total += amount

        msg += f"• {r['title']} ({qty} sales) — ₦{amount:,}\n"

    msg += (
        "\n──────────────────\n"
        f"🧾 Total Orders: {total_orders}\n"
        f"💰 Total Revenue: ₦{grand_total:,}\n"
        f"🕒 {_ng_now().strftime('%d %b %Y, %H:%M (NG)')}"
    )

    bot.send_message(target_chat_id, msg)


# ================= AUTOMATIC WEEKLY (GROUP) =================
def weekly_sales():
    since = _ng_now() - timedelta(days=7)
    send_sales_report(
        since,
        "📊 WEEKLY SALES REPORT",
        PAYMENT_NOTIFY_GROUP,
        silent_if_empty=True
    )


# ================= AUTOMATIC MONTHLY (GROUP) =================
def monthly_sales():
    now = _ng_now()
    since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    send_sales_report(
        since,
        f"📊 MONTHLY SALES REPORT ({now.strftime('%B %Y')})",
        PAYMENT_NOTIFY_GROUP,
        silent_if_empty=True
    )


# ================= SCHEDULER =================
def sales_report_scheduler():
    weekly_sent = False
    monthly_sent = False

    while True:
        now = _ng_now()

        # Friday 23:50
        if now.weekday() == 4 and now.hour == 23 and now.minute == 50:
            if not weekly_sent:
                weekly_sales()
                weekly_sent = True
        else:
            weekly_sent = False

        # Last day of month 23:50
        if now.day == _last_day_of_month(now) and now.hour == 23 and now.minute == 50:
            if not monthly_sent:
                monthly_sales()
                monthly_sent = True
        else:
            monthly_sent = False

        time.sleep(20)



# ▶️ START BACKGROUND REPORT THREAD
# ================== START SERVER ==================
if __name__ == "__main__":

    if BOT_MODE == "webhook":
        print("🌐 Running in WEBHOOK mode")

        try:
            bot.remove_webhook()
            bot.set_webhook(f"{WEBHOOK_URL}/telegram")
            print("✅ Telegram webhook set successfully")
        except Exception as e:
            print("❌ Failed to set webhook:", e)

        port = int(os.environ.get("PORT", 10000))
        print(f"🚀 Flask server running on port {port}")
        app.run(host="0.0.0.0", port=port)

    else:
        # fallback (local testing only)
        print("🤖 Running in POLLING mode")
        bot.infinity_polling(skip_pending=True)
