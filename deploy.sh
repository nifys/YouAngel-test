#!/bin/bash
echo "🚀 Запуск деплоя на Scalingo..."

# Проверка наличия токена
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: BOT_TOKEN не установлен"
    echo "Установите переменную окружения:"
    echo "export BOT_TOKEN='ваш_токен_бота'"
    exit 1
fi

# Сборка проекта
echo "📦 Подготовка файлов..."
rm -rf __pycache__
rm -f bot_data.json

# Деплой на Scalingo
echo "🚀 Отправка на Scalingo..."
git add .
git commit -m "Deploy to Scalingo"
git push scalingo master

echo "✅ Деплой завершен!"
echo "📋 Для проверки статуса: scalingo logs -f"