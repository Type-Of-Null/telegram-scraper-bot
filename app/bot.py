# bot.py
import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from scraper import scrape_headlines

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise SystemExit("Установите TELEGRAM_TOKEN в .env или в переменных окружения")

NEWS_URL = os.getenv("NEWS_URL", "https://lenta.ru")
HEADLINES_COUNT = int(os.getenv("HEADLINES_COUNT", "8"))
USE_CHROME = os.getenv("USE_CHROME", "true").lower() in ("1", "true", "yes")
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

# Создаем бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Хелпер для асинхронного вызова синхронной функции
async def fetch_headlines_async(url: str, limit: int = 8):
    # используем asyncio.to_thread для вызова синхронной функции в отдельном потоке
    return await asyncio.to_thread(
        scrape_headlines, url, limit, USE_CHROME, HEADLESS, 12
    )


# хендлеры команд
async def start_handler(message: types.Message):
    await message.answer(
        "<b>Новости без рекламы на сайте 😉!</b>\n\n"
        "Используй команду:\n"
        "<code>/seturl https://news.ru</code> — установить сайт\n"
        "<code>/headlines</code> — получить заголовки\n"
    )


async def seturl_handler(message: types.Message):
    global NEWS_URL
    args = message.get_args().strip()
    if not args:
        await message.answer("Использование: /seturl https://example.com")
        return
    NEWS_URL = args
    await message.answer(f"Целевой сайт установлен: {NEWS_URL}")


async def headlines_handler(message: types.Message):
    waiting = await message.answer("Собираю заголовки...")
    try:
        headlines = await fetch_headlines_async(NEWS_URL, HEADLINES_COUNT)
    except Exception as e:
        await waiting.edit_text(f"Ошибка при парсинге: <pre>{str(e)}</pre>")
        return

    if not headlines:
        await waiting.edit_text("Не удалось найти заголовки на странице.")
        return

    lines = []
    for title, url in headlines:
        safe_title = (
            title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        lines.append(f'• <a href="{url}">{safe_title}</a>')
    text = "\n".join(lines)
    await waiting.edit_text(text, disable_web_page_preview=True)


# register handlers (aiogram 3.x style)
dp.message.register(start_handler, Command(commands=["start", "help"]))
dp.message.register(seturl_handler, Command(commands=["seturl"]))
dp.message.register(headlines_handler, Command(commands=["headlines", "latest"]))


async def main():
    try:
        # стартуем поллинг
        await dp.start_polling(bot)
    finally:
        # корректное завершение
        await bot.session.close()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    print("Bot started. Ctrl+C to stop.")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Stopped.")
