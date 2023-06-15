import asyncio
import telegram_bot.config as config
import datetime
import math

import requests
from aiogram import Bot, types
from aiogram import Dispatcher
from aiogram.utils import executor

from telegram_bot.local_texts import ru_texts as texts
from telegram_bot.functions import get_marine_temp, forecast_for_3_hours, forecast_for_5_days, air_quality_status
from telegram_bot.utils import delta_time_f, get_emoji, escape_for_markdown


bot = Bot(token=config.telegram_token)

dp = Dispatcher(bot)


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.reply("Привет! Напиши мне название города и я пришлю сводку погоды")


async def send_startup_message():
    updates = await bot.get_updates()
    for update in updates:
        chat_id = update.message.chat.id
        await bot.send_message(chat_id=chat_id, text="Bot has been started")


@dp.message_handler()
async def get_weather(message: types.Message):
    try:
        dp.register_callback_query_handler(handle_callback_query)
        city = message.text.lower()

        response = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={city}&lang=ru&units=metric&appid={config.weather_api_token}")

        data = response.json()
        city = data["name"]
        cur_temp = data["main"]["temp"]
        feels_like_temp = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind = data["wind"]["speed"]
        delta_time = delta_time_f(data["timezone"])

        sunrise_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        sunset_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunset"])
        sunrise = sunrise_timestamp - delta_time
        sunset = sunset_timestamp - delta_time

        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]

        # продолжительность дня
        length_of_the_day = datetime.datetime.fromtimestamp(data["sys"]["sunset"]) - datetime.datetime.fromtimestamp(
            data["sys"]["sunrise"])

        # получаем значение погоды
        weather_description = data["weather"][0]["main"]
        wd = get_emoji(weather_description)

        zero_datetime = datetime.datetime(1970, 1, 1, 4, 0, 0)
        message_reply = (
            f"Локальное время: {(datetime.datetime.now() - delta_time).strftime('*%H:%M* %d-%m-%Y')}\n"
            f"Погода в городе: {city}\nТемпература: *{cur_temp}°C* {wd}\n"
            f"Ощущается как: *{round(feels_like_temp)}°C*\n"
            f"Влажность: *{humidity}%*\nДавление: *{math.ceil(pressure / 1.333)} мм.рт.ст*\nВетер: *{wind} м/с* \n"
        )
        if sunrise_timestamp > zero_datetime:
            message_reply += (
                f"Восход солнца: {sunrise.time()}\n"
                f"Закат солнца: {sunset.time()}\n"
                f"Продолжительность дня: {length_of_the_day}\n"
            )

        # Добавляем кнопки 
        # Создаем клавиатуру
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        # Создаем кнопку
        button_air_quality = types.InlineKeyboardButton(text="Качество воздуха",
                                                        callback_data=f"air_quality:{lat}:{lon}")
        button_forecast_3h = types.InlineKeyboardButton(text="Прогноз на 3 часа",
                                                        callback_data=f"forecast3h:{lat}:{lon}")
        button_forecast_5d = types.InlineKeyboardButton(text="Прогноз на 5 дней",
                                                        callback_data=f"forecast5d:{lat}:{lon}")
        button_marine_weather = types.InlineKeyboardButton(text="Температура воды",
                                                           callback_data=f"marine_weather:{lat}:{lon}")
        # Добавляем кнопку на клавиатуру
        keyboard.add(button_air_quality)
        keyboard.add(button_forecast_3h)
        keyboard.add(button_forecast_5d)
        keyboard.add(button_marine_weather)

        message_reply += ("\nХорошего дня!\n")

        message_reply = escape_for_markdown(message_reply)

        await message.reply(message_reply, parse_mode='MarkdownV2', reply_markup=keyboard)

    except requests.exceptions.HTTPError as error:
        if response.status_code == 429:
            await message.reply("Превышен лимит запросов к сайту погоды, восстановится завта")
        print(f"An HTTP error occurred: {error}")
    except requests.exceptions.RequestException as e:
        await message.reply("Ошибка при обращении к API погоды. Попробуйте позже.")
        print(f"Error: {e}")
    except KeyError:
        await message.reply("Получен некорректный ответ от API погоды. Попробуйте позже.")
        print("Error: Invalid response from weather API.")
    except Exception as e:
        await message.reply("Произошла ошибка. Попробуйте позже.")
        print(f"Error: {e}")


async def handle_callback_query(call: types.CallbackQuery):
    try:
        callback_data = call.data.split(':')
        lat = callback_data[1]
        lon = callback_data[2]

        if callback_data[0] == "air_quality":
            response_pollution = requests.get(
                f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={config.weather_api_token}")
            data_pollution = response_pollution.json()
            forecast = await get_air_quality(call, data_pollution)
        elif callback_data[0] == "marine_weather":
            response_water = requests.get(
                f"http://api.weatherapi.com/v1/marine.json?key={config.marine_wheather_api_token}&q={lat},{lon}")
            data_water = response_water.json()
            forecast = await get_marine_temp(data_water)
        else:
            response = requests.get(
                f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={config.weather_api_token}")
            data = response.json()
            if callback_data[0] == "forecast3h":
                forecast = await forecast_for_3_hours(data)
            elif callback_data[0] == "forecast5d":
                forecast = await forecast_for_5_days(data)
        forecast = escape_for_markdown(forecast)
        await bot.send_message(chat_id=call.message.chat.id, text=forecast, parse_mode='MarkdownV2')
        await bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Error handling query in buttons: {e}")


@dp.callback_query_handler(lambda c: c.data == 'air_quality_comment_short')
async def air_quality_comment_handler(callback_query: types.CallbackQuery):
    air_quality_comment_short = texts.air_quality_comment_short

    air_quality_comment_short = escape_for_markdown(air_quality_comment_short)
    # Отправляем комментарий в ответ на нажатие кнопки
    await bot.send_message(chat_id=callback_query.message.chat.id, text=air_quality_comment_short,
                           parse_mode='MarkdownV2')


@dp.callback_query_handler(lambda c: c.data == 'air_quality_comment_full')
async def air_quality_comment_handler(callback_query: types.CallbackQuery):
    air_quality_comment_full = texts.air_quality_comment_full

    # Отправляем комментарий в ответ на нажатие кнопки
    air_quality_comment_full = escape_for_markdown(air_quality_comment_full)
    await bot.send_message(chat_id=callback_query.message.chat.id, text=air_quality_comment_full,
                           parse_mode='MarkdownV2')


@dp.message_handler(commands=['air_quality'])
async def get_air_quality(call: types.CallbackQuery, data):
    air_quality_comment = await air_quality_status(data)
    air_quality_comment = escape_for_markdown(air_quality_comment)
    inline_keyboard = types.InlineKeyboardMarkup()
    comment_button_short = types.InlineKeyboardButton("Кратко о веществах", callback_data="air_quality_comment_short")
    comment_button_full = types.InlineKeyboardButton("Подробно о веществах", callback_data="air_quality_comment_full")
    inline_keyboard.add(comment_button_short)
    inline_keyboard.add(comment_button_full)
    # Отправляем сообщение с результатами и кнопкой
    await bot.send_message(chat_id=call.message.chat.id, text=air_quality_comment, reply_markup=inline_keyboard,
                           parse_mode='MarkdownV2')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(send_startup_message())
    executor.start_polling(dp, skip_updates=True)
