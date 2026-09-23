
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
                SELECT i.title, i.group_key, COALESCE(i.cashback_amount, 0)
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
            total_custom_cashback = 0

            for title, group_key, cb_amount in rows:
                key = group_key or f"single_{title}"
                if key not in groups:
                    groups[key] = {"title": title, "count": 0}
                    # Idan fims na cikin group guda ne, sau daya kawai za a dauki custom cashback din don gudun ninki (doubling)
                    if cb_amount and cb_amount > 0:
                        total_custom_cashback += cb_amount
                groups[key]["count"] += 1

            lines = []
            for g in groups.values():
                if g["count"] > 1:
                    lines.append(f"{g['title']} ({g['count']})")
                else:
                    lines.append(f"{g['title']}")

            titles_text = ", ".join(lines) if lines else "N/A"

            # ================= CASHBACK REWARD LOGIC =================
            if total_custom_cashback > 0:
                # 1. SABON TSARI: IDAN FIM(IN) YANA DA CUSTOM CASHBACK A DATABASE
                cashback = total_custom_cashback
                is_custom_cashback = True
            else:
                # 2. TSOHON TSARI: IDAN FIM(IN) BASHI DA CUSTOM CASHBACK
                cashback = (paid_amount // 200) * CASHBACK
                if cashback > 200:
                    cashback = 200
                is_custom_cashback = False

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

                # Samun jimillar balance dake cikin wallet din user bayan an kara cashback
                wallet_cur.execute(
                    """
                    SELECT balance FROM wallet_balance WHERE user_id=%s
                    """,
                    (user_id,)
                )
                user_balance_row = wallet_cur.fetchone()
                user_wallet_balance = user_balance_row[0] if user_balance_row else 0

                wallet_conn.commit()
                wallet_cur.close()
                wallet_conn.close()

                # ================= SABON TSARIN SAKON CASHBACK =================
                cb_kb = InlineKeyboardMarkup()
                cb_kb.add(
                    InlineKeyboardButton(
                        "💼 View Wallet", 
                        callback_data=f"view_cb_bal:{user_wallet_balance}",
                        style="primary"
                    )
                )

                cb_text = (
                    f"🎁 **Cashback Reward**🎉\n\n"
                    f"Wallet ID: `{user_id}`\n"
                    f"You received ₦{cashback} cashback,\n"
                    f"View your wallet to see available balance"
                )

                bot.send_message(user_id, cb_text, parse_mode="Markdown", reply_markup=cb_kb)

            conn.commit()
            cur.close()
            conn.close()

            # ================= SABON TSARIN SAKON PAYMENT SUCCESSFUL =================
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton(
                    "⬇️ DOWNLOAD NOW",
                    callback_data=f"deliver:{order_id}",
                    style="success"
                )
            )

            success_text = (
                f"🎉 **PAYMENT SUCCESSFUL!**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Mun Gode {full_name}\n\n"
                f"🎬 **Film:** {titles_text}\n"
                f"💵 **Amount Paid:** ₦{paid_amount}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎁 **Cashback Earned:** ₦{cashback}\n\n"
                f"✅ Biyan ya kammala! 😊\n"
                f"Danna DOWNLOAD domin sauke fim din\n"
                f"👇👇👇"
            )

            bot.send_message(user_id, success_text, parse_mode="Markdown", reply_markup=kb)

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

