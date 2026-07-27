import sqlite3
import time

DB_NAME = "bot_database.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_link TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS join_requests (
            user_id INTEGER,
            channel_id TEXT,
            PRIMARY KEY (user_id, channel_id)
        )
    ''')

    # Promo-kodlar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promo_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            days INTEGER,
            created_at REAL,
            expires_at REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_premium (
            user_id INTEGER PRIMARY KEY,
            expire_time REAL
        )
    ''')

    conn.commit()
    conn.close()


def add_user(user_id, username: str = None, full_name: str = None):
    if hasattr(user_id, 'id'):
        user_obj = user_id
        user_id = user_obj.id
        username = user_obj.username
        full_name = user_obj.full_name

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        conn.commit()
    except Exception as e:
        print(f"Foydalanuvchi qo'shishda xatolik: {e}")
    finally:
        conn.close()


def get_users_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def add_channel(channel_id: str, channel_link: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO channels (channel_id, channel_link) VALUES (?, ?)",
            (channel_id, channel_link)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Kanal qo'shishda xatolik: {e}")
        return False
    finally:
        conn.close()


def remove_channel(channel_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Kanalni o'chirishda xatolik: {e}")
        return False
    finally:
        conn.close()


def get_all_channels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_link FROM channels")
    channels = cursor.fetchall()
    conn.close()
    return channels


def add_join_request(user_id: int, channel_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO join_requests (user_id, channel_id) VALUES (?, ?)",
            (user_id, channel_id)
        )
        conn.commit()
    except Exception as e:
        print(f"So'rovni saqlashda xatolik: {e}")
    finally:
        conn.close()


def check_join_request(user_id: int, channel_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM join_requests WHERE user_id = ? AND channel_id = ?",
        (user_id, channel_id)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_promo_code(code: str, days: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        clean_code = code.strip()
        current_time = time.time()
        expires_at = current_time + (days * 86400)

        cursor.execute(
            "INSERT OR REPLACE INTO promo_codes (code, days, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (clean_code, days, current_time, expires_at)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Promo qo'shishda xatolik: {e}")
        return False
    finally:
        conn.close()


def clean_expired_promos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promo_codes WHERE expires_at < ?", (time.time(),))
    conn.commit()
    conn.close()


def get_all_promo_codes():
    clean_expired_promos()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, days FROM promo_codes ORDER BY created_at ASC")
    promos = cursor.fetchall()
    conn.close()
    return promos


def remove_promo_by_index(index: int) -> str:
    promos = get_all_promo_codes()
    if 0 <= index < len(promos):
        code_to_delete = promos[index][0]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM promo_codes WHERE code = ?", (code_to_delete,))
        conn.commit()
        conn.close()
        return code_to_delete
    return None


def check_and_use_promo(user_id: int, code: str) -> str:
    clean_expired_promos()
    conn = get_connection()
    cursor = conn.cursor()

    clean_code = code.strip()
    cursor.execute("SELECT days FROM promo_codes WHERE TRIM(code) = TRIM(?)", (clean_code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return "❌ Bu promo-kod mavjud emas yoki muddati o'tib ketgan!"

    days = row[0]
    # Foydalanuvchi kodni kiritgan paytdan boshlab kunlarni hisoblaymiz (masalan: 1 kun = 86400 sekund)
    expire_time = time.time() + (days * 86400)

    # Foydalanuvchiga VIP beramiz va vaqtini yozamiz
    cursor.execute("INSERT OR REPLACE INTO users_premium (user_id, expire_time) VALUES (?, ?)", (user_id, expire_time))
    # Promo-kod ishlatilgandan keyin bazadan o'chiriladi
    cursor.execute("DELETE FROM promo_codes WHERE TRIM(code) = TRIM(?)", (clean_code,))

    conn.commit()
    conn.close()
    return f"🎉 Tabriklaymiz! Sizga {days} kunlik Premium obuna muvaffaqiyatli faollashtirildi!"


def is_user_premium(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT expire_time FROM users_premium WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        # Agar vaqti hali kelmagan bo'lsa (hozirgi vaqtdan katta bo'lsa), True qaytaradi
        if row and row[0] > time.time():
            return True
        return False
    finally:
        conn.close()