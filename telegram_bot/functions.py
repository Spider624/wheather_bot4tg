import datetime

from telegram_bot.utils import get_emoji


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
    # formatting first
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


async def get_marine_temp(json_data):
    data = json_data
    forecastday = data["forecast"]["forecastday"][0]
    water_temp_list = [hour["water_temp_c"] for hour in forecastday["hour"]]

    max_water_temp = max(water_temp_list)
    min_water_temp = min(water_temp_list)
    water_message = f"t° Температура воды сегодня\n MAX:   {max_water_temp}°C\n MIN:   {min_water_temp}°C\n"
    water_message = f"```{water_message}```"
    return water_message


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
    forecast_message += "{:<{}}   ".format("Погода         ```", max_time_width) + "```   ```".join(
        weather_description[1:]) + "``` \n"

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