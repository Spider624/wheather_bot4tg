import os
import datetime
import requests
import asyncio
import math
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor 

import config

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
        
def delta_time_f(data_timezone):
    tm =  datetime.timedelta(0 , 10800)
    tp = datetime.timedelta(0 , data_timezone)
    delta_time = tm - tp
    return delta_time
        
@dp.message_handler()
async def get_weather(message: types.Message):
    try:
        dp.register_callback_query_handler(handle_callback_query)
        city = message.text.lower()
        
        response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q={city}&lang=ru&units=metric&appid={config.weather_api_token}")

        data = response.json()
        city = data["name"]
        cur_temp = data["main"]["temp"]
        feels_like_temp = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        pressure = data["main"]["pressure"]
        wind = data["wind"]["speed"]
        # tm =  datetime.timedelta(0 , 10800)
        # tp = datetime.timedelta(0 , data["timezone"])
        # delta_time = tm - tp
        delta_time = delta_time_f(data["timezone"])

        sunrise_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        sunset_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunset"])
        sunrise = sunrise_timestamp - delta_time
        sunset = sunset_timestamp - delta_time
        
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]
        response_pollution = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={config.weather_api_token}")
        data_pollution = response_pollution.json()
        
        #Air Quality Index. Possible values: 1, 2, 3, 4, 5. Where 1 = Good, 2 = Fair, 3 = Moderate, 4 = Poor, 5 = Very Poor.
        air_pollution_index = data_pollution["list"][0]["main"]["aqi"]
        air_pollution_co = data_pollution["list"][0]["components"]["co"]

        # продолжительность дня
        length_of_the_day = datetime.datetime.fromtimestamp(data["sys"]["sunset"]) -       datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        
        code_to_smile = {
            "Clear": "Ясно \U00002600",
            "Clouds": "Облачно \U00002601",
            "Rain": "Дождь \U00002614",
            "Drizzle": "Дождь \U00002614",
            "Thunderstorm": "Гроза \U000026A1",
            "Snow": "Снег \U0001F328",
            "Mist": "Туман \U0001F32B"
        }
        
        # получаем значение погоды
        weather_description = data["weather"][0]["main"]

        if weather_description in code_to_smile:
            wd = code_to_smile[weather_description]
        else:
            # если эмодзи для погоды нет, выводим другое сообщение
            wd = "Посмотри в окно, я не понимаю, что там за погода..."

        zero_datetime = datetime.datetime(1970, 1, 1, 4, 0, 0)
        message_reply = (
            f"Локальное время: {(datetime.datetime.now() - delta_time).strftime('*%H:%M* %d-%m-%Y')}\n"
            f"Погода в городе: {city}\nТемпература: *{cur_temp}°C* {wd}\n"
            f"Ощущается как: *{round(feels_like_temp)}°C*\n"
            f"Влажность: *{humidity}%*\nДавление: *{math.ceil(pressure/1.333)} мм.рт.ст*\nВетер: *{wind} м/с* \n"
        )
        if sunrise_timestamp > zero_datetime:
            message_reply += (
                f"Восход солнца: {sunrise.time()}\n"
                f"Закат солнца: {sunset.time()}\n"
                f"Продолжительность дня: {length_of_the_day}\n"
            )
        message_reply += (
            f"\nИндекс загрязнения воздуха: *{air_pollution_index}*\n _1 = Хорошее, 2 = Удовлетворительное, 3 = Умеренное, 4 = Плохое, 5 = Очень плохое._\n"
            f"Содержание угарного газа: *{air_pollution_co}*\n"
        )
        message_reply += ("\nХорошего дня!\n")
        # Добавляем кнопки 
        # Создаем клавиатуру
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        # Создаем кнопку
        button_forecast_3h = types.InlineKeyboardButton(text="Прогноз на 3 часа", callback_data=f"forecast3h:{lat}:{lon}")
        button_forecast_5d = types.InlineKeyboardButton(text="Прогноз на 5 дней", callback_data=f"forecast5d:{lat}:{lon}")
        # Добавляем кнопку на клавиатуру
        keyboard.add(button_forecast_3h)
        keyboard.add(button_forecast_5d)
        
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

def escape_for_markdown(message_reply):
        message_reply = message_reply.replace('-', r'\-')
        message_reply = message_reply.replace('.', r'\.')
        message_reply = message_reply.replace('!', r'\!')
        message_reply = message_reply.replace('=', r'\=')
        message_reply = message_reply.replace('|', r'\|')
        message_reply = message_reply.replace('<', r'\<')
        message_reply = message_reply.replace('>', r'\>')
        #message_reply = message_reply.replace('`', r'\`')
        return message_reply

async def handle_callback_query(call: types.CallbackQuery):
    try:
        callback_data = call.data.split(':')
        lat = callback_data[1]
        lon = callback_data[2]
        
        response = requests.get(f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={config.weather_api_token}")
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

async def forecast_for_3_hours(data):
    json_data = data
    forecast_list = json_data["list"][:3]

    times = [forecast["dt_txt"].split()[1].split(":")[0] + ":00" for forecast in forecast_list]
    max_time_width = max(len(time) for time in times)

    temperature_values = ["{:>5}".format(round(forecast["main"]["temp"] - 273.15)) for forecast in forecast_list]
    feels_like_values = ["{:>5}".format(round(forecast["main"]["feels_like"] - 273.15)) for forecast in forecast_list]
    humidity_values = ["{:>5}".format(forecast["main"]["humidity"]) for forecast in forecast_list]
    pressure_values = ["{:>5}".format(round(forecast["main"]["pressure"] * 0.75)) for forecast in forecast_list]
    wind_speed_values = ["{:>5}".format(round(forecast["wind"]["speed"])) for forecast in forecast_list]

    forecast_message = "Прогноз               |3 часа |6 часов\n"
    forecast_message += "{:<{}} | ".format("Температура °C", max_time_width) + " | ".join(temperature_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Ощущается °C  ", max_time_width) + " | ".join(feels_like_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Влажность %   ", max_time_width) + " | ".join(humidity_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Давление м.р.с", max_time_width) + " | ".join(pressure_values[1:]) + " \n"
    forecast_message += "{:<{}} | ".format("Ветер   м/с   ", max_time_width) + " | ".join(wind_speed_values[1:]) + "\n"

    forecast_message = f"```{forecast_message}```"
    return forecast_message

async def forecast_for_5_days(data):
    json_data = data
    forecast_list = json_data["list"]

    forecast_message = "Дата      | День  | Ночь  | Осадки      \n"

    moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))

    # Получение текущего времени в Москве
    current_datetime = datetime.datetime.now(moscow_timezone)

    # Определение ближайшего интервала прогноза на 12 часов дня и 3 часа ночи
    if current_datetime.hour < 12:
        interval = ("12:00:00", "00:00:00")
        skip_current_day = False
    elif current_datetime.hour < 15:
        interval = ("15:00:00", "03:00:00")
        skip_current_day = False
    else:
        interval = ("12:00:00", "03:00:00")
        skip_current_day = True

    filtered_forecasts = [forecast for forecast in forecast_list if forecast["dt_txt"].split()[1] in interval]

    # Пропуск текущего дня, если необходимо
    if skip_current_day:
        filtered_forecasts = filtered_forecasts[1:]

    for i in range(0, len(filtered_forecasts), 2):
        forecast_day = filtered_forecasts[i]
        forecast_night = filtered_forecasts[i + 1] if i + 1 < len(filtered_forecasts) else None

        date_str = forecast_day["dt_txt"].split()[0]
        time_str = forecast_day["dt_txt"].split()[1]

        forecast_datetime = datetime.datetime.strptime(date_str + " " + time_str, "%Y-%m-%d %H:%M:%S")
        forecast_datetime = forecast_datetime.replace(tzinfo=moscow_timezone)

        formatted_date = forecast_datetime.strftime("%d-%m")
        day_temp = round(forecast_day["main"]["temp"] - 273.15)
        night_temp = round(forecast_night["main"]["temp"] - 273.15) if forecast_night else None
        precipitation = round(forecast_day["pop"] * 100)
        weather_description = forecast_day["weather"][0]["main"]

        code_to_smile = {
            "Clear": "\U00002600",
            "Clouds": "\U00002601",
            "Rain": "\U00002614",
            "Drizzle": "\U00002614",
            "Thunderstorm": "\U000026A1",
            "Snow": "\U0001F328",
            "Mist": "\U0001F32B"
        }

        emoji = code_to_smile.get(weather_description, "🌡️")

        forecast_message += f"{formatted_date} | {day_temp:>3}°C | {night_temp or '-':>3}°C | {precipitation:>3}% | {emoji:>2}\n"
    forecast_message = f"```{forecast_message}```"
    return forecast_message

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(send_startup_message())
    executor.start_polling(dp, skip_updates=True)