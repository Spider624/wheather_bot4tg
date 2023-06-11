import datetime
import requests
import asyncio
import math
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor 

import  texts
import config

def get_emoji(weather_description):
    code_to_smile = {
        "Clear": "\U00002600",
        "Clouds": "\U00002601",
        "Rain": "\U00002614",
        "Drizzle": "\U00002614",
        "Thunderstorm": "\U000026A1",
        "Snow": "\U0001F328",
        "Mist": "\U0001F32B"
    }
    return code_to_smile.get(weather_description, "🌡️")


def escape_for_markdown(message_reply):
        message_reply = message_reply.replace('-', r'\-')
        message_reply = message_reply.replace('.', r'\.')
        message_reply = message_reply.replace('!', r'\!')
        message_reply = message_reply.replace('=', r'\=')
        message_reply = message_reply.replace('|', r'\|')
        message_reply = message_reply.replace('<', r'\<')
        message_reply = message_reply.replace('>', r'\>')
        message_reply = message_reply.replace('(', '\[').replace(')', '\]')
        #message_reply = message_reply.replace('`', r'\`')
        return message_reply

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
        delta_time = delta_time_f(data["timezone"])

        sunrise_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        sunset_timestamp = datetime.datetime.fromtimestamp(data["sys"]["sunset"])
        sunrise = sunrise_timestamp - delta_time
        sunset = sunset_timestamp - delta_time
        
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]

        # продолжительность дня
        length_of_the_day = datetime.datetime.fromtimestamp(data["sys"]["sunset"]) -       datetime.datetime.fromtimestamp(data["sys"]["sunrise"])
        
        # получаем значение погоды
        weather_description = data["weather"][0]["main"]
        wd = get_emoji(weather_description)

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

        # Добавляем кнопки 
        # Создаем клавиатуру
        keyboard = types.InlineKeyboardMarkup(resize_keyboard=True)
        # Создаем кнопку
        button_air_quality = types.InlineKeyboardButton(text="Качество воздуха", callback_data=f"air_quality:{lat}:{lon}")
        button_forecast_3h = types.InlineKeyboardButton(text="Прогноз на 3 часа", callback_data=f"forecast3h:{lat}:{lon}")
        button_forecast_5d = types.InlineKeyboardButton(text="Прогноз на 5 дней", callback_data=f"forecast5d:{lat}:{lon}")
        # Добавляем кнопку на клавиатуру
        keyboard.add(button_air_quality)
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


async def handle_callback_query(call: types.CallbackQuery):
    try:
        callback_data = call.data.split(':')
        lat = callback_data[1]
        lon = callback_data[2]
        
        if callback_data[0] == "air_quality":
            response_pollution = requests.get(f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={config.weather_api_token}")
            data_pollution = response_pollution.json()
            forecast = await get_air_quality(call, data_pollution)
        else:
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


@dp.callback_query_handler(lambda c: c.data == 'air_quality_comment_short')
async def air_quality_comment_handler(callback_query: types.CallbackQuery):
    air_quality_comment_short = texts.air_quality_comment_short

    air_quality_comment_short = escape_for_markdown(air_quality_comment_short)
    # Отправляем комментарий в ответ на нажатие кнопки
    await bot.send_message(chat_id=callback_query.message.chat.id, text=air_quality_comment_short, parse_mode='MarkdownV2')
 
    
@dp.callback_query_handler(lambda c: c.data == 'air_quality_comment_full')
async def air_quality_comment_handler(callback_query: types.CallbackQuery):
  
    air_quality_comment_full = texts.air_quality_comment_full 
    
    # Отправляем комментарий в ответ на нажатие кнопки
    air_quality_comment_full = escape_for_markdown(air_quality_comment_full)
    await bot.send_message(chat_id=callback_query.message.chat.id, text=air_quality_comment_full, parse_mode='MarkdownV2')


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
    await bot.send_message(chat_id=call.message.chat.id, text=air_quality_comment, reply_markup=inline_keyboard, parse_mode='MarkdownV2')


async def air_quality_status(data):
    
    air_pollution_index = data["list"][0]["main"]["aqi"]
    air_pollution_co = data["list"][0]["components"]["co"]
    air_pollution_no = data["list"][0]["components"]["no"]
    air_pollution_no2 = data["list"][0]["components"]["no2"]
    air_pollution_o3 = data["list"][0]["components"]["o3"]
    air_pollution_so2 = data["list"][0]["components"]["so2"]
    air_pollution_pm2_5 = data["list"][0]["components"]["pm2_5"]
    air_pollution_pm10 = data["list"][0]["components"]["pm10"]
    air_pollution_nh3 = data["list"][0]["components"]["nh3"]

    aqi_levels = {
        "Хорошее": {
            "Index": 1,
            "SO2": [0.0, 20.0],
            "NO2": [0.0, 40.0],
            "PM10": [0.0, 20.0],
            "PM2.5": [0.0, 10.0],
            "O3": [0.0, 60.0],
            "CO": [0.0, 4400.0]
        },
        "Нормальное": {
            "Index": 2,
            "SO2": [20.0, 80.0],
            "NO2": [40.0, 70.0],
            "PM10": [20.0, 50.0],
            "PM2.5": [10.0, 25.0],
            "O3": [60.0, 100.0],
            "CO": [4400.0, 9400.0]
        },
        "_Среднее_": {
            "Index": 3,
            "SO2": [80.0, 250.0],
            "NO2": [70.0, 150.0],
            "PM10": [50.0, 100.0],
            "PM2.5": [25.0, 50.0],
            "O3": [100.0, 140.0],
            "CO": [9400.0, 12400.0]
        },
        "*Плохое*": {
            "Index": 4,
            "SO2": [250.0, 350.0],
            "NO2": [150.0, 200.0],
            "PM10": [100.0, 200.0],
            "PM2.5": [50.0, 75.0],
            "O3": [140.0, 180.0],
            "CO": [12400.0, 15400.0]
        },
        "*Очень плохое !!!*": {
            "Index": 5,
            "SO2": [350.0, float("inf")],
            "NO2": [200.0, float("inf")],
            "PM10": [200.0, float("inf")],
            "PM2.5": [75.0, float("inf")],
            "O3": [180.0, float("inf")],
            "CO": [15400.0, float("inf")]
        }
    }
    
    air_quality_categories = {}
    #formatting first
    f = "`"
    for parameter, value in {
        "SO2": air_pollution_so2,
        "NO2": air_pollution_no2,
        "PM10": air_pollution_pm10,
        "PM2.5": air_pollution_pm2_5,
        "O3": air_pollution_o3,
        "CO": air_pollution_co
    }.items():
        for category, thresholds in aqi_levels.items():
            if thresholds[parameter][0] <= value <= thresholds[parameter][1]:
                air_quality_categories[parameter] = category
                break
    air_quality_index_label = ["Unknown", "Хорошее", "Нормальное", "_Среднее_", "Плохое", "Очень плохое"]
    air_quality_message = f"""Текущее Качество воздуха:
{f}Air Quality Index:{f} *\n        {air_pollution_index} ({air_quality_index_label[air_pollution_index]})*
Концентрация:
{f}CO    :{f} {air_pollution_co} ({air_quality_categories.get("CO")})
{f}NO2   :{f} {air_pollution_no2}   ({air_quality_categories.get("NO2")})
{f}O3    :{f} {air_pollution_o3} ({air_quality_categories.get("O3")})
{f}SO2   :{f} {air_pollution_so2}   ({air_quality_categories.get("SO2")})
{f}PM2,5 :{f} {air_pollution_pm2_5}  ({air_quality_categories.get("PM2.5")})
{f}PM10  :{f} {air_pollution_pm10} ({air_quality_categories.get("PM10")})
Не влияют на качество воздуха:
{f}NO    :{f} {air_pollution_no}
{f}NH3   :{f} {air_pollution_nh3}"""

    return air_quality_message


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
    precipitation = ["{:>5}".format(round(round(forecast["pop"] * 100))) for forecast in forecast_list]
    weather_description = ["{:>5}".format(get_emoji(forecast["weather"][0]["main"])) for forecast in forecast_list]
    
    forecast_message = "Прогноз               |3 часа |6 часов\n"
    forecast_message += "{:<{}} | ".format("Температура °C", max_time_width) + " | ".join(temperature_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Ощущается   °C", max_time_width) + " | ".join(feels_like_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Влажность    %", max_time_width) + " | ".join(humidity_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Давление м.р.с", max_time_width) + " | ".join(pressure_values[1:]) + " \n"
    forecast_message += "{:<{}} | ".format("Ветер      м/с", max_time_width) + " | ".join(wind_speed_values[1:]) + "\n"
    forecast_message += "{:<{}} | ".format("Осадки       %", max_time_width) + " | ".join(precipitation[1:]) + "\n"
    forecast_message += "{:<{}}   ".format("Погода         ```", max_time_width) + "```   ```".join(weather_description[1:]) + "``` \n"

    forecast_message = f"```{forecast_message}```"
    return forecast_message


async def forecast_for_5_days(data):
    json_data = data
    forecast_list = json_data["list"]
    
    forecast_message = "Дата     |  Макс |   Мин | Осадки \n"

    day_forecasts = {}

    for forecast in forecast_list:
        forecast_date = forecast["dt_txt"].split()[0]
        if forecast_date not in day_forecasts:
            day_forecasts[forecast_date] = []
        day_forecasts[forecast_date].append(forecast)

    for date, forecasts in day_forecasts.items():
        temps = [forecast["main"]["temp"] - 273.15 for forecast in forecasts]
        min_temp = round(min(temps))
        max_temp = round(max(temps))
        precipitation = round(forecasts[0]["pop"] * 100)
        weather_description = forecasts[0]["weather"][0]["main"]

        emoji = get_emoji(weather_description)

        formatted_date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m")
        forecast_message += f"{formatted_date}| {max_temp:>4}°C| {min_temp:>4}°C| {precipitation:>3}%| ```{emoji:>0}``` \n"

    forecast_message = f"```{forecast_message}```"
    return forecast_message


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(send_startup_message())
    executor.start_polling(dp, skip_updates=True)