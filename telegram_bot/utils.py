import datetime

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

def delta_time_f(data_timezone):
    tm = datetime.timedelta(0, 10800)
    tp = datetime.timedelta(0, data_timezone)
    delta_time = tm - tp
    return delta_time