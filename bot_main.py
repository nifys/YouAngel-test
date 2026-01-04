
import json
import time
import re
import os
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

print("=" * 60)
print("🤖 БОТ 'ТВОЙ АНГЕЛ' - ЗАПУСК")
print("=" * 60)

# Конфигурация
BOT_TOKEN = os.environ.get('8166283745:AAEHBhb2L80_gU5xD-AXy4s3d8426UnZxVk')
OWNER_ID = int(os.environ.get('OWNER_ID', '8294608065'))

if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    exit(1)

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Списки администраторов по уровням
ADMIN_LEVELS = {
    "owner": ["OWNER"],  # Владелец (ВСЕ ПРАВА)
    "head": ["HEAD"],    # Руководитель  
    "deputy": ["DEPUTY"], # Зам. руководителя
    "tester": ["TESTER"], # Тестировщик
    "media": ["MEDIA"],   # Медиа
    "monitor": ["MONITOR"], # Следящий за админами
    "normal": ["Ниф", "Админ2", "Админ3", "Админ4", "Админ5", "Админ6", "Админ7"]  # Обычные админы
}

# Права для каждого уровня (ТОЛЬКО ВЛАДЕЛЕЦ ИМЕЕТ АДМИН ПРАВА)
ADMIN_PERMISSIONS = {
    "owner": ["all"],  # ВЛАДЕЛЕЦ - ВСЕ ПРАВА
    "head": ["checklog", "checkadmin", "newtt", "testlog", "admlog", "chats", "leave", "leaveadm"],  # НЕТ addadmin, removeadmin, addspec, broad
    "deputy": ["testlog", "admlog", "checkadmin", "chats", "leave", "leaveadm"],
    "tester": ["testlog", "chats", "leave", "leaveadm"],
    "media": ["newtt", "chats", "leave", "leaveadm"],
    "monitor": ["admlog", "checkadmin", "chats", "leave", "leaveadm"],
    "normal": ["chats", "leave", "leaveadm"]  # Обычные админы
}

# Глобальные переменные
user_choices = {}
active_admins = {}
admin_levels = {}
active_chats = {}
banned_users = {}
special_groups = set()
admin_logs = []
message_logs = {}
last_update_id = 0

# Хранилище данных
DATA_FILE = "bot_data.json"

def save_data():
    """Сохраняем все данные в файл"""
    data = {
        'user_choices': user_choices,
        'active_admins': active_admins,
        'admin_levels': admin_levels,
        'special_groups': list(special_groups),
        'banned_users': {k: v.isoformat() for k, v in banned_users.items()},
        'last_update_id': last_update_id,
        'admin_logs': admin_logs[-1000:],
        'message_logs': message_logs
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")

def load_data():
    """Загружаем данные из файла"""
    global user_choices, active_admins, admin_levels, special_groups, banned_users, last_update_id, admin_logs, message_logs
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_choices = data.get('user_choices', {})
            active_admins = data.get('active_admins', {})
            admin_levels = data.get('admin_levels', {})
            special_groups = set(data.get('special_groups', []))
            
            banned_users_raw = data.get('banned_users', {})
            banned_users = {}
            for k, v in banned_users_raw.items():
                try:
                    banned_users[int(k)] = datetime.fromisoformat(v)
                except:
                    pass
            
            last_update_id = data.get('last_update_id', 0)
            admin_logs = data.get('admin_logs', [])
            message_logs = data.get('message_logs', {})
            
            print(f"📂 Загружено: {len(user_choices)} пользователей, {len(active_admins)} админов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
    else:
        print("📂 Файл данных не найден, начинаем с чистого листа")

def add_admin_log(admin_id: int, action: str, details: str = ""):
    """Добавить лог действия администратора"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'admin_id': admin_id,
        'action': action,
        'details': details
    }
    admin_logs.append(log_entry)
    if len(admin_logs) > 1000:
        admin_logs.pop(0)

def add_message_log(admin_id: int, user_id: int, message: str):
    """Добавить лог сообщения от админа к пользователю"""
    if admin_id not in message_logs:
        message_logs[admin_id] = []
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'message': message
    }
    message_logs[admin_id].append(log_entry)
    if len(message_logs[admin_id]) > 100:
        message_logs[admin_id].pop(0)

def is_banned(user_id):
    """Проверка бана"""
    if user_id in banned_users:
        ban_time = banned_users[user_id]
        if datetime.now() > ban_time:
            del banned_users[user_id]
            save_data()
            return False
        return True
    return False

def ban_user(user_id, days=7):
    """Забанить пользователя"""
    banned_users[user_id] = datetime.now() + timedelta(days=days)
    save_data()

def unban_user(user_id):
    """Разбанить пользователя"""
    if user_id in banned_users:
        del banned_users[user_id]
        save_data()

# Загружаем данные
load_data()

# ========== API ФУНКЦИИ ==========

def send_api_request(method, params=None):
    """Отправка запроса к Telegram API"""
    url = f"{API_URL}/{method}"
    
    if params:
        data = urllib.parse.urlencode(params).encode('utf-8')
    else:
        data = None
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result
    except Exception as e:
        print(f"❌ API ошибка: {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    """Отправка сообщения"""
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    return send_api_request('sendMessage', params)

def edit_message_text(chat_id, message_id, text, reply_markup=None):
    """Редактирование сообщения"""
    params = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    return send_api_request('editMessageText', params)

def answer_callback_query(callback_query_id, text=None):
    """Ответ на callback query"""
    params = {'callback_query_id': callback_query_id}
    if text:
        params['text'] = text
    return send_api_request('answerCallbackQuery', params)

def get_updates():
    """Получение обновлений"""
    global last_update_id
    
    params = {'offset': last_update_id + 1, 'timeout': 30}
    result = send_api_request('getUpdates', params)
    
    if result and result.get('ok'):
        updates = result.get('result', [])
        for update in updates:
            last_update_id = update['update_id']
        return updates
    return []

# ========== ФУНКЦИИ ПРАВ ==========

def is_owner(user_id):
    """Проверка, является ли пользователь владельцем"""
    return user_id == OWNER_ID

def get_admin_level(user_id):
    """Получить уровень админа по ID"""
    return admin_levels.get(user_id, "normal")

def has_permission(user_id, permission):
    """Проверка прав доступа"""
    if is_owner(user_id):
        return True  # ВЛАДЕЛЕЦ ИМЕЕТ ВСЕ ПРАВА
    
    level = get_admin_level(user_id)
    permissions = ADMIN_PERMISSIONS.get(level, [])
    
    return "all" in permissions or permission in permissions

def get_admin_name(user_id):
    """Получить имя админа по его ID"""
    for name, admin_id in active_admins.items():
        if admin_id == user_id:
            return name
    return None

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========

def process_start(user_id, chat_id, message_id=None):
    """Обработка /start"""
    if is_banned(user_id):
        send_message(chat_id, "🚫 Вы заблокированы на 7 дней.\nДля обжалования используйте /report")
        return
    
    keyboard = []
    for admin_name in ADMIN_LEVELS["normal"]:
        if admin_name in active_admins:
            keyboard.append([{
                'text': admin_name,
                'callback_data': f'choose_{admin_name}'
            }])
    
    if not keyboard:
        send_message(chat_id, "⚠️ В данный момент нет доступных администраторов.")
        return
    
    reply_markup = {'inline_keyboard': keyboard}
    send_message(chat_id, "🐱 Привет, котенок! Выбери своего админа:", reply_markup=reply_markup)

def process_callback_query(query_id, user_id, chat_id, message_id, data):
    """Обработка callback query"""
    answer_callback_query(query_id)
    
    if is_banned(user_id):
        edit_message_text(chat_id, message_id, "🚫 Вы заблокированы.")
        return
    
    if data.startswith('choose_'):
        admin_name = data.replace('choose_', '')
        user_choices[user_id] = admin_name
        save_data()
        
        edit_message_text(chat_id, message_id, 
            f"✅ Отлично! Ты выбрал(а) админа {admin_name}.\n\n"
            f"Теперь пиши любые сообщения - они будут отправляться {admin_name}.\n"
            f"Чтобы сменить админа - напиши /change")
    
    elif data.startswith('chat_'):
        if not has_permission(user_id, "chats"):
            edit_message_text(chat_id, message_id, "🚫 Нет доступа")
            return
        
        target_id = int(data.replace('chat_', ''))
        active_chats[user_id] = target_id
        edit_message_text(chat_id, message_id, 
            f"✅ Чат с пользователем {target_id} выбран.\n"
            f"Теперь все твои сообщения будут отправляться ему.\n"
            f"Чтобы выйти - напиши /leave")

def process_text_message(user_id, chat_id, text, username=None, chat_type="private"):
    """Обработка текстового сообщения"""
    
    if chat_id in special_groups and chat_type in ['group', 'supergroup']:
        if not text.startswith('/'):
            return
    
    if is_banned(user_id):
        send_message(chat_id, "🚫 Вы заблокированы.")
        return
    
    # Проверка на контакты
    if '@' in text or re.search(r'\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text):
        ban_user(user_id)
        send_message(chat_id,
            "🚫 Запрещено делиться контактами!\n"
            "Бан на 7 дней. /report для обжалования.")
        return
    
    # Если админ в режиме чата с пользователем
    if user_id in active_chats:
        target_id = active_chats[user_id]
        send_message(target_id, f"💌 От админа:\n{text}")
        
        add_message_log(user_id, target_id, text)
        add_admin_log(user_id, "message_to_user", f"to:{target_id}")
        
        send_message(chat_id, "✅ Отправлено пользователю")
    
    # Если пользователь пишет своему админу
    else:
        admin_name = user_choices.get(user_id)
        if not admin_name:
            send_message(chat_id, "⚠️ Сначала выбери админа через /start")
            return
        
        admin_tg_id = active_admins.get(admin_name)
        if admin_tg_id:
            try:
                send_message(admin_tg_id, 
                    f"💌 Для {admin_name} (от пользователя {user_id}):\n\n{text}")
                send_message(chat_id, f"✅ Отправлено {admin_name}")
                add_admin_log(admin_tg_id, "received_from_user", f"from:{user_id}")
            except:
                send_message(chat_id, f"❌ {admin_name} недоступен")
        else:
            send_message(chat_id,
                f"📝 Сообщение сохранено для {admin_name}\n"
                f"Админ получит его когда появится.")

# ========== КОМАНДЫ ==========

def process_command(user_id, chat_id, command, args, username=None, chat_type="private"):
    """Обработка команд"""
    command = command.lower()
    
    # Ограничение команд в спец-группах
    if chat_id in special_groups and chat_type in ['group', 'supergroup']:
        allowed_commands = ['/addadmin', '/removeadmin', '/listadmins', '/help', '/addspec', 
                           '/editname', '/checklog', '/checkadmin', '/newtt', '/testlog', '/admlog', 
                           '/broad', '/reply']
        if command not in [c[1:] for c in allowed_commands]:
            send_message(chat_id, "🚫 Эта команда не доступна в этой группе.")
            return
    
    # ========== КОМАНДЫ ТОЛЬКО ДЛЯ ВЛАДЕЛЬЦА ==========
    
    # Команда /editname - ТОЛЬКО для владельца
    if command == 'editname':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if len(args) < 2:
            send_message(chat_id,
                "📝 Используй: /editname [старое_название] [новое_название]\n"
                f"Пример: /editname Ниф Ниф-Новый")
            return
        
        old_name = args[0]
        new_name = args[1]
        
        if old_name not in active_admins:
            send_message(chat_id, f"❌ Админ с именем '{old_name}' не найден")
            return
        
        if new_name in active_admins:
            send_message(chat_id, f"❌ Имя '{new_name}' уже занято")
            return
        
        # Меняем имя в active_admins
        admin_id = active_admins[old_name]
        del active_admins[old_name]
        active_admins[new_name] = admin_id
        
        # Меняем имя в user_choices у всех пользователей
        for uid, chosen_name in list(user_choices.items()):
            if chosen_name == old_name:
                user_choices[uid] = new_name
        
        # Меняем в списке обычных админов
        if old_name in ADMIN_LEVELS["normal"]:
            index = ADMIN_LEVELS["normal"].index(old_name)
            ADMIN_LEVELS["normal"][index] = new_name
        
        save_data()
        
        send_message(admin_id, f"ℹ️ Ваше имя было изменено:\nСтарое: {old_name}\nНовое: {new_name}")
        send_message(chat_id, f"✅ Имя админа изменено:\n{old_name} → {new_name}")
        add_admin_log(user_id, "edit_name", f"{old_name}→{new_name}")
        return
    
    # Команда /addadmin - ТОЛЬКО для владельца
    if command == 'addadmin':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if len(args) < 3:
            send_message(chat_id,
                "📝 Используй: /addadmin [user_id] [имя] [уровень]\n"
                f"Уровни: head, deputy, tester, media, monitor, normal\n"
                f"Имена (для normal): {', '.join(ADMIN_LEVELS['normal'])}")
            return
        
        try:
            admin_id = int(args[0])
        except:
            send_message(chat_id, "❌ ID должен быть числом")
            return
        
        admin_name = args[1]
        admin_level = args[2].lower()
        
        if admin_level not in ADMIN_PERMISSIONS:
            send_message(chat_id, f"❌ Неверный уровень. Доступные: {', '.join(ADMIN_PERMISSIONS.keys())}")
            return
        
        if admin_level == "normal" and admin_name not in ADMIN_LEVELS["normal"]:
            send_message(chat_id, f"❌ Нет такого имени для обычных админов. Доступные: {', '.join(ADMIN_LEVELS['normal'])}")
            return
        
        # Удаляем если уже есть с таким ID
        for name, aid in list(active_admins.items()):
            if aid == admin_id:
                del active_admins[name]
        
        # Добавляем админа
        active_admins[admin_name] = admin_id
        admin_levels[admin_id] = admin_level
        save_data()
        
        # Отправляем сообщение новому админу
        level_names = {
            "head": "Руководитель",
            "deputy": "Заместитель руководителя", 
            "tester": "Тестировщик",
            "media": "Медиа",
            "monitor": "Следящий за админами",
            "normal": "Обычный админ"
        }
        
        level_name = level_names.get(admin_level, admin_level)
        welcome_msg = (f"🎉 Вы назначены администратором.\n"
                      f"Имя: {admin_name}\n"
                      f"Уровень: {level_name}")
        
        if admin_level == "normal":
            welcome_msg += f"\n\nИспользуйте /chats для просмотра ваших чатов."
        
        send_message(admin_id, welcome_msg)
        send_message(chat_id, f"✅ Админ {admin_name} добавлен (ID: {admin_id}, Уровень: {admin_level})")
        add_admin_log(user_id, "add_admin", f"name:{admin_name}, level:{admin_level}")
        return
    
    # Команда /removeadmin - ТОЛЬКО для владельца
    if command == 'removeadmin':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if not args:
            send_message(chat_id, "📝 Используй: /removeadmin [имя]")
            return
        
        admin_name = args[0]
        
        if admin_name not in active_admins:
            send_message(chat_id, "❌ Админ не найден")
            return
        
        admin_id = active_admins[admin_name]
        del active_admins[admin_name]
        
        if admin_id in admin_levels:
            del admin_levels[admin_id]
        
        save_data()
        
        send_message(admin_id, f"ℹ️ Вы удалены с поста администратора {admin_name}.")
        send_message(chat_id, f"✅ Админ {admin_name} удален")
        add_admin_log(user_id, "remove_admin", f"name:{admin_name}")
        return
    
    # Команда /addspec - ТОЛЬКО для владельца
    if command == 'addspec':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if chat_type in ['group', 'supergroup']:
            special_groups.add(chat_id)
            save_data()
            send_message(chat_id, "✅ Спец-доступ активирован в этой группе!")
            add_admin_log(user_id, "add_spec_group", f"chat_id:{chat_id}")
        else:
            send_message(chat_id, "⚠️ Эта команда работает только в группах")
        return
    
    # Команда /broad - ТОЛЬКО для владельца
    if command == 'broad':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if not args:
            send_message(chat_id, "📝 Используй: /broad [текст рассылки]")
            return
        
        broadcast_text = " ".join(args)
        
        sent = 0
        failed = 0
        
        for uid in set(user_choices.keys()):
            if not is_banned(uid):
                try:
                    send_message(uid, f"📢 РАССЫЛКА:\n\n{broadcast_text}")
                    sent += 1
                    time.sleep(0.1)
                except:
                    failed += 1
        
        send_message(chat_id, f"✅ Рассылка завершена:\nОтправлено: {sent}\nНе удалось: {failed}")
        add_admin_log(user_id, "broadcast", f"sent:{sent}, failed:{failed}")
        return
    
    # Команда /reply - ТОЛЬКО для владельца
    if command == 'reply':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if len(args) < 3:
            send_message(chat_id, "📝 Используй: /reply [user_id] [текст] [yes/no]\n\n'yes' - разблокировать\n'no' - оставить как есть")
            return
        
        try:
            target_id = int(args[0])
        except:
            send_message(chat_id, "❌ user_id должен быть числом")
            return
        
        reply_text = " ".join(args[1:-1])
        action = args[-1].lower()
        
        if action == 'yes':
            unban_user(target_id)
            status = "✅ Пользователь разблокирован"
        elif action == 'no':
            status = "ℹ️ Бан не снят"
        else:
            send_message(chat_id, "❌ Последний аргумент должен быть 'yes' или 'no'")
            return
        
        send_message(target_id, f"📩 Ответ на вашу жалобу:\n\n{reply_text}\n\n{status}")
        send_message(chat_id, f"✅ Ответ отправлен пользователю {target_id}\n{status}")
        add_admin_log(user_id, "reply_report", f"to:{target_id}, action:{action}")
        return
    
    # Команда /listadmins - ТОЛЬКО для владельца
    if command == 'listadmins':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if not active_admins:
            send_message(chat_id, "📭 Нет назначенных админов")
            return
        
        admin_list = []
        for name, tg_id in active_admins.items():
            level = admin_levels.get(tg_id, "normal")
            admin_list.append(f"• {name} (ID: {tg_id}, Уровень: {level})")
        
        send_message(chat_id, "👮 Назначенные админы:\n" + "\n".join(admin_list))
        return
    
    # ========== КОМАНДЫ ДЛЯ РУКОВОДИТЕЛЯ ==========
    
    # Команда /checklog - для руководителя
    if command == 'checklog':
        if not has_permission(user_id, "checklog"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        logs_text = "📊 ЛОГИ АДМИНОВ:\n\n"
        for log in admin_logs[-50:]:
            logs_text += f"🕒 {log['timestamp']}\n👤 ID: {log['admin_id']}\n📝 {log['action']}\n"
            if log['details']:
                logs_text += f"📋 {log['details']}\n"
            logs_text += "─" * 30 + "\n"
        
        if len(logs_text) > 4000:
            logs_text = logs_text[:4000] + "\n... (логи обрезаны)"
        
        send_message(chat_id, f"```\n{logs_text}\n```")
        add_admin_log(user_id, "check_log", "просмотр логов")
        return
    
    # Команда /checkadmin - для руководителя и зам. руководителя
    if command == 'checkadmin':
        if not has_permission(user_id, "checkadmin"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        if not active_admins:
            send_message(chat_id, "📭 Нет назначенных админов")
            return
        
        admin_list = []
        for name, admin_id in active_admins.items():
            level = admin_levels.get(admin_id, "normal")
            admin_list.append(f"• {name} (ID: {admin_id}, Уровень: {level})")
        
        send_message(chat_id, "👮 СПИСОК АДМИНОВ:\n" + "\n".join(admin_list))
        add_admin_log(user_id, "check_admin", "просмотр списка админов")
        return
    
    # Команда /newtt - для руководителя и медиа
    if command == 'newtt':
        if not has_permission(user_id, "newtt"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        if len(args) < 2:
            send_message(chat_id,
                "📝 Используй: /newtt [ссылка] [название видео]\n"
                "Пример: /newtt https://tiktok.com/video1 Крутое видео!")
            return
        
        link = args[0]
        video_title = " ".join(args[1:])
        
        message_text = f"🎬 НОВОЕ ВИДЕО В НАШЕМ ТИКТОКЕ!!\n\n\"{video_title}\"\n\n👇👇👇\n{link}\n{link}\n{link}\n\nСмотри скорее!!"
        
        sent = 0
        failed = 0
        
        for uid in set(user_choices.keys()):
            if not is_banned(uid):
                try:
                    send_message(uid, message_text)
                    sent += 1
                    time.sleep(0.1)
                except:
                    failed += 1
        
        send_message(chat_id, f"✅ Рассылка TikTok видео завершена:\nОтправлено: {sent}\nНе удалось: {failed}")
        add_admin_log(user_id, "new_tt", f"title:{video_title[:50]}")
        return
    
    # Команда /testlog - для руководителя, зам. руководителя и тестировщика
    if command == 'testlog':
        if not has_permission(user_id, "testlog"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        if len(args) < 2:
            send_message(chat_id,
                "📝 Используй: /testlog [текст] [да/нет]\n"
                "Пример: /testlog Нашел баг в отправке сообщений да")
            return
        
        log_text = " ".join(args[:-1])
        is_error = args[-1].lower() == 'да'
        
        error_status = "Ошибка" if is_error else "Не ошибка"
        
        report_msg = (f"🚨 НОВЫЙ ТЕСТ ЛОГ!!!\n\n"
                     f"Отправил: @{username if username else 'нет_юзернейма'}\n"
                     f"Ошибка?: {error_status}\n"
                     f"Суть: {log_text}")
        
        # Отправляем владельцу
        send_message(OWNER_ID, report_msg)
        send_message(chat_id, "✅ Тест-лог отправлен владельцу")
        add_admin_log(user_id, "test_log", f"error:{is_error}")
        return
    
    # Команда /admlog - для руководителя, зам. руководителя и следящего
    if command == 'admlog':
        if not has_permission(user_id, "admlog"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        # Фильтруем обычных админов
        normal_admins = []
        for name, admin_id in active_admins.items():
            if name in ADMIN_LEVELS["normal"]:
                normal_admins.append(admin_id)
        
        if not normal_admins:
            send_message(chat_id, "📭 Нет активных обычных админов")
            return
        
        logs_text = "📊 ЛОГИ ОБЫЧНЫХ АДМИНОВ:\n\n"
        
        for admin_id in normal_admins:
            admin_name = get_admin_name(admin_id)
            user_count = len([uid for uid, name in user_choices.items() if name == admin_name])
            message_count = len(message_logs.get(admin_id, []))
            
            logs_text += f"👤 {admin_name} (ID: {admin_id})\n"
            logs_text += f"   Пользователей: {user_count}\n"
            logs_text += f"   Сообщений отправлено: {message_count}\n"
            
            last_messages = message_logs.get(admin_id, [])[-3:]
            for msg in last_messages:
                logs_text += f"   🕒 {msg['timestamp'][11:19]}: {msg['message'][:30]}...\n"
            
            logs_text += "─" * 30 + "\n"
        
        send_message(chat_id, logs_text)
        add_admin_log(user_id, "adm_log", "просмотр логов админов")
        return
    
    # ========== ОСНОВНЫЕ КОМАНДЫ ==========
    
    if command == 'start':
        process_start(user_id, chat_id)
    
    elif command == 'change':
        if is_banned(user_id):
            send_message(chat_id, "🚫 Вы заблокированы.")
            return
        
        keyboard = []
        for admin_name in ADMIN_LEVELS["normal"]:
            if admin_name in active_admins:
                keyboard.append([{
                    'text': admin_name,
                    'callback_data': f'choose_{admin_name}'
                }])
        
        if not keyboard:
            send_message(chat_id, "⚠️ Нет доступных администраторов")
            return
        
        reply_markup = {'inline_keyboard': keyboard}
        send_message(chat_id, "Выбери нового админа:", reply_markup=reply_markup)
    
    elif command == 'report':
        if not args:
            send_message(chat_id, "📝 Используй: /report [текст жалобы]")
            return
        
        report_text = " ".join(args)
        send_message(OWNER_ID, f"🚨 РЕПОРТ от {user_id}:\n\n{report_text}\n\nДля ответа: /reply {user_id} [текст] [yes/no]")
        send_message(chat_id, "✅ Ваша жалоба отправлена владельцу.")
    
    elif command == 'chats':
        if not has_permission(user_id, "chats"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        admin_name = get_admin_name(user_id)
        if not admin_name:
            send_message(chat_id, "🚫 Только для админов")
            return
        
        user_list = []
        for uid, chosen_admin in user_choices.items():
            if chosen_admin == admin_name and not is_banned(uid):
                user_list.append(uid)
        
        if not user_list:
            send_message(chat_id, "📭 Нет активных чатов")
            return
        
        keyboard = []
        for uid in user_list[:15]:
            keyboard.append([{
                'text': f"👤 Пользователь {uid}",
                'callback_data': f'chat_{uid}'
            }])
        
        reply_markup = {'inline_keyboard': keyboard}
        send_message(chat_id, f"💬 Чаты админа {admin_name} ({len(user_list)}):", reply_markup=reply_markup)
        add_admin_log(user_id, "view_chats", f"users:{len(user_list)}")
    
    elif command == 'leave':
        if user_id in active_chats:
            del active_chats[user_id]
        send_message(chat_id, "✅ Режим ответа выключен")
    
    elif command == 'leaveadm':
        if not has_permission(user_id, "leaveadm"):
            send_message(chat_id, "🚫 Нет доступа!")
            return
        
        admin_name = get_admin_name(user_id)
        if admin_name:
            if admin_name in active_admins:
                del active_admins[admin_name]
            
            if user_id in admin_levels:
                del admin_levels[user_id]
            
            save_data()
            
            # Кикаем из спец-групп
            for group_id in special_groups:
                try:
                    send_api_request('banChatMember', {
                        'chat_id': group_id,
                        'user_id': user_id,
                        'until_date': int(time.time() + 30)
                    })
                except:
                    pass
            
            for group_id in special_groups:
                send_message(group_id, f"👋 Администратор {admin_name} ушел с поста по собственному желанию!")
            
            send_message(chat_id, "✅ Вы успешно ушли с поста администратора.")
            add_admin_log(user_id, "leave_admin", f"name:{admin_name}")
        else:
            send_message(chat_id, "❌ Вы не являетесь администратором.")
    
    elif command == 'help':
        if chat_id in special_groups and chat_type in ['group', 'supergroup']:
            level = get_admin_level(user_id)
            if is_owner(user_id):
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - ВЛАДЕЛЕЦ</b>

<b>Управление админами:</b>
/addadmin [ID] [Имя] [уровень] - Добавить админа
/editname [старое] [новое] - Изменить имя админа
/removeadmin [Имя] - Удалить админа
/listadmins - Список админов
/addspec - Активировать спец-доступ
/reply [ID] [текст] [yes/no] - Ответ на жалобу
/broad [текст] - Рассылка всем

<b>Мониторинг:</b>
/checklog - Логи всех админов
/checkadmin - Список всех админов
/admlog - Логи обычных админов
/newtt [ссылка] [название] - Рассылка TikTok
/testlog [текст] [да/нет] - Тест-лог
                """
            elif level == "head":
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - РУКОВОДИТЕЛЬ</b>

<b>Команды:</b>
/checklog - Логи всех админов
/checkadmin - Список всех админов
/newtt [ссылка] [название] - Рассылка TikTok
/testlog [текст] [да/нет] - Тест-лог владельцу
/admlog - Логи обычных админов

<b>Личные команды:</b>
/chats - Мои чаты
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста
                """
            elif level == "deputy":
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - ЗАМ. РУКОВОДИТЕЛЯ</b>

<b>Команды:</b>
/testlog [текст] [да/нет] - Тест-лог владельцу
/admlog - Логи обычных админов
/checkadmin - Список всех админов

<b>Личные команды:</b>
/chats - Мои чаты
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста
                """
            elif level == "tester":
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - ТЕСТИРОВЩИК</b>

<b>Команды:</b>
/testlog [текст] [да/нет] - Тест-лог владельцу

<b>Личные команды:</b>
/chats - Мои чаты
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста
                """
            elif level == "media":
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - МЕДИА</b>

<b>Команды:</b>
/newtt [ссылка] [название] - Рассылка TikTok

<b>Личные команды:</b>
/chats - Мои чаты
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста
                """
            elif level == "monitor":
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - СЛЕДЯЩИЙ</b>

<b>Команды:</b>
/admlog - Логи обычных админов
/checkadmin - Список всех админов

<b>Личные команды:</b>
/chats - Мои чаты
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста
                """
            else:
                help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - АДМИН ГРУППА</b>

<b>Команды админов:</b>
/chats - Мои чаты (пользователи)
/leave - Выйти из режима ответа
/leaveadm - Уйти с поста админа
                """
        else:
            help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ"</b>

<b>Основные команды:</b>
/start - Выбрать админа
/change - Сменить админа  
/report [текст] - Отправить жалобу
/help - Эта справка

⚠️ <b>Правила:</b> 
- Не отправляйте контакты
- За нарушения - бан на 7 дней
            """
        send_message(chat_id, help_text)
    
    else:
        send_message(chat_id, "❌ Неизвестная команда. Используй /help")

# ========== ОБРАБОТКА ОБНОВЛЕНИЙ ==========

def process_update(update):
    """Обработка одного обновления"""
    try:
        if 'message' in update:
            msg = update['message']
            user_id = msg['from']['id']
            chat_id = msg['chat']['id']
            text = msg.get('text', '').strip()
            username = msg['from'].get('username')
            chat_type = msg['chat']['type']
            
            if text.startswith('/'):
                parts = text.split()
                command = parts[0][1:]  # Убираем /
                args = parts[1:] if len(parts) > 1 else []
                process_command(user_id, chat_id, command, args, username, chat_type)
            elif text:
                process_text_message(user_id, chat_id, text, username, chat_type)
        
        elif 'callback_query' in update:
            query = update['callback_query']
            query_id = query['id']
            user_id = query['from']['id']
            message = query['message']
            chat_id = message['chat']['id']
            message_id = message['message_id']
            data = query['data']
            
            process_callback_query(query_id, user_id, chat_id, message_id, data)
    
    except Exception as e:
        print(f"⚠️ Ошибка обработки: {e}")

def bot_polling():
    """Основной цикл бота"""
    print("\n" + "=" * 60)
    print("✅ БОТ ЗАПУЩЕН И РАБОТАЕТ!")
    print("=" * 60)
    
    error_count = 0
    while True:
        try:
            updates = get_updates()
            if updates:
                print(f"📨 Получено {len(updates)} обновлений")
                for update in updates:
                    process_update(update)
            error_count = 0
        except Exception as e:
            error_count += 1
            print(f"⚠️ Ошибка в цикле: {e}")
            if error_count > 10:
                print("❌ Слишком много ошибок, перезапуск...")
                time.sleep(10)
                error_count = 0
        time.sleep(0.5)

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    try:
        print("🔍 Проверяем соединение с Telegram...")
        me = send_api_request('getMe')
        if me and me.get('ok'):
            bot_name = me['result']['username']
            print(f"✅ Бот @{bot_name} готов к работе!")
            
            send_message(OWNER_ID, 
                f"🤖 Бот запущен!\n"
                f"Владелец: {OWNER_ID}\n\n"
                f"<b>КОМАНДЫ ВЛАДЕЛЬЦА:</b>\n"
                f"/addadmin [ID] [Имя] [уровень]\n"
                f"/editname [старое] [новое]\n"
                f"/removeadmin [Имя]\n"
                f"/listadmins\n"
                f"/addspec\n"
                f"/reply [ID] [текст] [yes/no]\n"
                f"/broad [текст]\n"
                f"/checklog\n"
                f"/checkadmin\n"
                f"/newtt [ссылка] [название]\n"
                f"/testlog [текст] [да/нет]\n"
                f"/admlog")
            
            bot_polling()
        else:
            print("❌ Неверный токен бота или нет интернета")
            print("Проверьте BOT_TOKEN")
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
        save_data()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        save_data()
