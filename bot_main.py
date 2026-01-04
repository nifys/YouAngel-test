import json
import time
import re
import os
from datetime import datetime, timedelta
import urllib.request
import urllib.parse

print("=" * 60)
print("🤖 БОТ 'ТВОЙ АНГЕЛ' - SCALINGO VERSION")
print("=" * 60)

# Конфигурация из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8403035412:AAHePhUD99Xke_DfghRp_UnfmuMytMgXwIE')
OWNER_ID = int(os.environ.get('OWNER_ID', '8294608065'))
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
ADMINS = ["Ниф", "Админ2", "Админ3", "Админ4", "Админ5", "Админ6", "Админ7"]

print(f"📱 Бот: {BOT_TOKEN[:15]}...")
print(f"👑 Владелец: {OWNER_ID}")
print(f"👥 Админы: {', '.join(ADMINS)}")

# Глобальные переменные
user_choices = {}
active_admins = {}
active_chats = {}
banned_users = {}
special_groups = set()
last_update_id = 0

# Безопасное хранилище
DATA_FILE = "bot_data.json"

def save_data():
    """Сохраняем все данные в файл"""
    data = {
        'user_choices': user_choices,
        'active_admins': active_admins,
        'special_groups': list(special_groups),
        'banned_users': {k: v.isoformat() for k, v in banned_users.items()},
        'last_update_id': last_update_id
    }
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения: {e}")

def load_data():
    """Загружаем данные из файла"""
    global user_choices, active_admins, special_groups, banned_users, last_update_id
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            user_choices = data.get('user_choices', {})
            active_admins = data.get('active_admins', {})
            special_groups = set(data.get('special_groups', []))
            
            banned_users_raw = data.get('banned_users', {})
            banned_users = {}
            for k, v in banned_users_raw.items():
                try:
                    banned_users[int(k)] = datetime.fromisoformat(v)
                except:
                    pass
            
            last_update_id = data.get('last_update_id', 0)
            print(f"📂 Загружено: {len(user_choices)} пользователей, {len(active_admins)} админов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
    else:
        print("📂 Файл данных не найден, начинаем с чистого листа")

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

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========

def is_owner(user_id):
    """Проверка, является ли пользователь владельцем"""
    return user_id == OWNER_ID

def is_admin(user_id):
    """Проверка, является ли пользователь админом"""
    return user_id in active_admins.values()

def get_admin_name(user_id):
    """Получить имя админа по его ID"""
    for name, admin_id in active_admins.items():
        if admin_id == user_id:
            return name
    return None

def process_start(user_id, chat_id, message_id=None):
    """Обработка /start"""
    if is_banned(user_id):
        send_message(chat_id, "🚫 Вы заблокированы на 7 дней.\nДля обжалования используйте /report")
        return
    
    keyboard = []
    for admin_name in ADMINS:
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
        if not is_admin(user_id):
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
    
    if '@' in text or re.search(r'\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}', text):
        ban_user(user_id)
        send_message(chat_id,
            "🚫 Запрещено делиться контактами!\n"
            "Бан на 7 дней. /report для обжалования.")
        return
    
    if user_id in active_chats:
        target_id = active_chats[user_id]
        send_message(target_id, f"💌 От админа:\n{text}")
        send_message(chat_id, "✅ Отправлено пользователю")
    else:
        admin_name = user_choices.get(user_id)
        if not admin_name:
            send_message(chat_id, "⚠️ Сначала выбери админа через /start")
            return
        
        admin_tg_id = active_admins.get(admin_name)
        if admin_tg_id:
            try:
                send_message(admin_tg_id, 
                    f"💌 Для {admin_name} (от {user_id}):\n\n{text}")
                send_message(chat_id, f"✅ Отправлено {admin_name}")
            except:
                send_message(chat_id, f"❌ {admin_name} недоступен")
        else:
            send_message(chat_id,
                f"📝 Сообщение сохранено для {admin_name}\n"
                f"Админ получит его когда появится.")

def process_command(user_id, chat_id, command, args, username=None, chat_type="private"):
    """Обработка команд"""
    command = command.lower()
    
    if chat_id in special_groups and chat_type in ['group', 'supergroup']:
        allowed_commands = ['/addadmin', '/removeadmin', '/listadmins', '/help', '/addspec']
        if command not in allowed_commands:
            send_message(chat_id, "🚫 Эта команда не доступна в этой группе.")
            return
    
    if command == '/start':
        process_start(user_id, chat_id)
    
    elif command == '/change':
        if is_banned(user_id):
            send_message(chat_id, "🚫 Вы заблокированы.")
            return
        
        keyboard = []
        for admin_name in ADMINS:
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
    
    elif command == '/addadmin':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if len(args) < 2:
            send_message(chat_id,
                "📝 Используй: /addadmin [user_id] [имя]\n"
                f"Доступные имена: {', '.join(ADMINS)}\n"
                "user_id можно узнать у @userinfobot")
            return
        
        try:
            admin_id = int(args[0])
        except:
            send_message(chat_id, "❌ ID должен быть числом")
            return
        
        admin_name = args[1]
        
        if admin_name not in ADMINS:
            send_message(chat_id, f"❌ Нет такого имени. Доступные: {', '.join(ADMINS)}")
            return
        
        for name, aid in list(active_admins.items()):
            if aid == admin_id:
                del active_admins[name]
        
        active_admins[admin_name] = admin_id
        save_data()
        
        send_message(admin_id, f"🎉 Поздравляем! Вы были назначены администратором {admin_name}.\nИспользуйте /chats для просмотра ваших чатов.")
        
        send_message(chat_id, f"✅ Админ {admin_name} добавлен (ID: {admin_id})")
    
    elif command == '/removeadmin':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if not args:
            send_message(chat_id, "📝 Используй: /removeadmin [имя]")
            return
        
        admin_name = args[0]
        
        if admin_name not in ADMINS:
            send_message(chat_id, f"❌ Нет такого админа")
            return
        
        if admin_name in active_admins:
            admin_id = active_admins[admin_name]
            del active_admins[admin_name]
            save_data()
            
            send_message(admin_id, f"ℹ️ Вы были удалены с поста администратора {admin_name}.")
            
            send_message(chat_id, f"✅ Админ {admin_name} удален")
        else:
            send_message(chat_id, "❌ Админ не найден")
    
    elif command == '/addspec':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if chat_type in ['group', 'supergroup']:
            special_groups.add(chat_id)
            save_data()
            send_message(chat_id, "✅ Спец-доступ активирован в этой группе!")
        else:
            send_message(chat_id, "⚠️ Эта команда работает только в группах")
    
    elif command == '/report':
        if not args:
            send_message(chat_id, "📝 Используй: /report [текст жалобы]")
            return
        
        report_text = " ".join(args)
        
        send_message(OWNER_ID, f"🚨 РЕПОРТ от {user_id}:\n\n{report_text}\n\nДля ответа: /reply {user_id} [текст] [yes/no]")
        send_message(chat_id, "✅ Ваша жалоба отправлена владельцу.")
    
    elif command == '/reply':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if len(args) < 3:
            send_message(chat_id, "📝 Используй: /reply [user_id] [текст] [yes/no]\n\n'yes' - разблокировать пользователя\n'no' - оставить как есть")
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
    
    elif command == '/broad':
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
    
    elif command == '/chats':
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
    
    elif command == '/leave':
        if user_id in active_chats:
            del active_chats[user_id]
        send_message(chat_id, "✅ Режим ответа выключен")
    
    elif command == '/leaveadm':
        admin_name = get_admin_name(user_id)
        if admin_name:
            if admin_name in active_admins:
                del active_admins[admin_name]
                save_data()
            
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
        else:
            send_message(chat_id, "❌ Вы не являетесь администратором.")
    
    elif command == '/help':
        if chat_id in special_groups and chat_type in ['group', 'supergroup']:
            help_text = """
🤖 <b>БОТ "ТВОЙ АНГЕЛ" - ГРУППА АДМИНОВ</b>

<b>Команды владельца:</b>
/addadmin [ID] [Имя] - Добавить админа
/removeadmin [Имя] - Удалить админа
/listadmins - Список админов
/addspec - Активировать спец-доступ
/reply [ID] [текст] [yes/no] - Ответ на жалобу
/broad [текст] - Рассылка всем

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
- Уважайте других пользователей
- За нарушения - бан на 7 дней
            """
        send_message(chat_id, help_text)
    
    elif command == '/listadmins':
        if not is_owner(user_id):
            send_message(chat_id, "🚫 Только владелец!")
            return
        
        if not active_admins:
            send_message(chat_id, "📭 Нет назначенных админов")
            return
        
        admin_list = []
        for name, tg_id in active_admins.items():
            admin_list.append(f"• {name} (ID: {tg_id})")
        
        send_message(chat_id, "👮 Назначенные админы:\n" + "\n".join(admin_list))
    
    else:
        send_message(chat_id, "❌ Неизвестная команда. Используй /help")

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
                command = parts[0]
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
                f"🤖 Бот запущен на Scalingo!\n"
                f"Владелец: {OWNER_ID}\n"
                f"Команды:\n"
                f"/addadmin [ID] [Имя] - добавить админа\n"
                f"/broad [текст] - рассылка\n"
                f"/reply [ID] [текст] [yes/no] - ответ на жалобу")
            
            bot_polling()
        else:
            print("❌ Неверный токен бота или нет интернета")
            print("Проверьте переменную окружения BOT_TOKEN")
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
        save_data()
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        save_data()