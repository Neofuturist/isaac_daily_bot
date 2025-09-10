import logging
import os
import json
from calendar import weekday, month
from datetime import time
from datetime import datetime
import json
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

import config

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Имя файла для хранения подписок
SUBSCRIPTIONS_FILE = "subscriptions.json"


def load_subscriptions():
    """Загружает список подписанных пользователей из файла."""
    try:
        if os.path.exists(SUBSCRIPTIONS_FILE):
            with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Не удалось загрузить подписки, создаем новый файл. Ошибка: {e}")
        return set()


def save_subscriptions(subscriptions):
    """Сохраняет список подписанных пользователей в файл."""
    try:
        with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(subscriptions), f, ensure_ascii=False, indent=2)
        logger.info(f"Подписки сохранены. Всего подписчиков: {len(subscriptions)}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении подписок: {e}")


# Загружаем подписки при старте
subscribed_users = load_subscriptions()
logger.info(f"Загружено {len(subscribed_users)} подписчиков")


async def send_daily_notification(context: ContextTypes.DEFAULT_TYPE):
    """Отправляет информацию о тематическом дейлике всем подписанным пользователям."""
    global subscribed_users
    subscribed_users = load_subscriptions()

    if not subscribed_users:
        logger.info("Нет подписчиков для отправки уведомления.")
        return

    # Получаем данные о празднике (или None если его нет)
    holiday_data = check_if_daily_is_thematic()

    if not holiday_data:
        logger.info("Сегодня не тематический дейлик. Уведомление не отправляется.")
        return
    # Получаем скриншот для этого праздника
    screenshot_path = "screenshots/" + holiday_data['screenshot']
    holiday_name = holiday_data['name']

    # Формируем сообщение
    caption = f"🌚 Сегодня {holiday_name} - тематический дейлик! Удачи!"

    successful_sends = 0
    failed_sends = 0
    users_to_notify = subscribed_users.copy()

    for user_id in users_to_notify:
        try:
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=caption
                    )
            else:
                await context.bot.send_message(chat_id=user_id, text=caption)

            successful_sends += 1
            logger.info(f"Уведомление отправлено пользователю {user_id}")

        except Exception as e:
            logger.info(f"Error: {e}")
            pass

    logger.info(f"Уведомления отправлены. Успешно: {successful_sends}, Не удалось: {failed_sends}")


def check_if_daily_is_thematic():
    """Проверяет тематические даты из JSON файла. Возвращает объект с данными или None."""
    from datetime import datetime
    import json

    today = datetime.now()
    month_day = (today.month, today.day)

    try:
        with open('thematic_dates.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        for holiday in data['thematic_dates']:
            if (holiday['month'], holiday['day']) == month_day:
                logger.info(f"Найден тематический дейлик: {holiday['name']}")
                return holiday  # Возвращаем весь объект с данными

    except FileNotFoundError:
        logger.warning("Файл thematic_dates.json не найден")
    except json.JSONDecodeError:
        logger.error("Ошибка чтения thematic_dates.json")

    logger.info("Сегодня нет тематического дейлика")
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подписывает пользователя на уведомления."""
    user_id = update.effective_user.id

    if user_id not in subscribed_users:
        subscribed_users.add(user_id)
        save_subscriptions(subscribed_users)

        await update.message.reply_text(
            "Ты успешно подписался на уведомления о тематических дейликах в The Binding of Isaac! 🎮\n\n"
            "Ожидай сообщение около 13:00 по МСК, если сегодня будет забег.\n"
            "Чтобы отписаться, используй команду /stop"
        )
        logger.info(f"Пользователь {user_id} подписался на уведомления.")
    else:
        await update.message.reply_text("Ты уже подписан на уведомления! ✅")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отписывает пользователя от уведомлений."""
    user_id = update.effective_user.id

    if user_id in subscribed_users:
        subscribed_users.discard(user_id)
        save_subscriptions(subscribed_users)

        await update.message.reply_text(
            "Ты отписался от уведомлений 💩\n"
            "Если передумаешь - просто напиши /start"
        )
        logger.info(f"Пользователь {user_id} отписался от уведомлений.")
    else:
        await update.message.reply_text("Ты и так не подписан на уведомления. 🤷")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику подписчиков."""
    user_id = update.effective_user.id

    total_subscribers = len(subscribed_users)
    await update.message.reply_text(
        f"📊 Статистика бота:\n"
        f"Всего подписчиков: {total_subscribers}\n"
        f"Твой ID: {user_id}"
    )
    logger.info(f"Пользователь {user_id} запросил статистику")


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает информацию о сегодняшнем тематическом дейлике."""
    user_id = update.effective_user.id

    # Получаем данные о празднике
    holiday_data = check_if_daily_is_thematic()

    if holiday_data:
        # Если сегодня тематический дейлик
        screenshot_path = "screenshots/" + holiday_data['screenshot']
        holiday_name = holiday_data['name']
        caption = f"🌚 Сегодня {holiday_name} - тематический дейлик! Удачи!"

        try:
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=caption
                    )
            else:
                await update.message.reply_text(caption)

            logger.info(f"Пользователь {user_id} запросил информацию о сегодняшнем дейлике")

        except Exception as e:
            logger.error(f"Ошибка отправки фото пользователю {user_id}: {e}")
            await update.message.reply_text(caption)
    else:
        # Если сегодня нет тематического дейлика
        await update.message.reply_text(
            "📅 Сегодня нет тематического дейлика.\n"
        )
        logger.info(f"Пользователь {user_id} запросил информацию - сегодня нет дейлика")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список доступных команд."""
    help_text = (
        "🎮 Доступные команды:\n\n"
        "/start - Подписаться на уведомления о тематических дейликах\n"
        "/stop - Отписаться от уведомлений\n"
        "/today - Проверить, есть ли сегодня тематический дейлик\n"
        "/stats - Показать статистику подписчиков\n"
        "/help - Показать это сообщение\n\n"
        "Бот автоматически присылает уведомления в 13:00 по МСК, если сегодня тематический забег!"
    )
    await update.message.reply_text(help_text)
    logger.info(f"Пользователь {update.effective_user.id} запросил помощь")


def main():
    """Запускает бота."""
    application = Application.builder().token(config.TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("today", today))
    application.add_handler(CommandHandler("help", help_command))

    # Настраиваем ежедневное уведомление
    job_queue = application.job_queue
    time_utc = time(10, 0, 0)  # 10:00 UTC = 13:00 МСК
    job_queue.run_daily(send_daily_notification, time=time_utc, name="daily_isaac_notification")

    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()