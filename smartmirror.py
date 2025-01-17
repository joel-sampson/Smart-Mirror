#!/usr/bin/env python3
# smartmirror.py
# requirements
# requests, feedparser, traceback, Pillow

import sys
from PIL import Image, ImageTk
from contextlib import contextmanager
from tkinter import (BOTH, BOTTOM, E, LEFT, Label, N, RIGHT, S, TOP, Tk, W, YES, Frame)
import argparse
import asyncio
import feedparser
import locale
import python_weather
import threading
import time
import traceback

LOCALE_LOCK = threading.Lock()

ui_locale = ''  # e.g. 'fr_FR' fro French, '' as default
time_format = 12  # 12 or 24
date_format = "%b %d, %Y"  # check python doc for strftime() for options
xlarge_text_size = 94
large_text_size = 48
medium_text_size = 28
small_text_size = 18
xsmall_text_size = 14
# trying to avoid hard coding
parser = argparse.ArgumentParser()
parser.add_argument("--location", "-l", default="None", required=True, help="Location for weather data")
parser.add_argument("--fahrenheit", "-f", default=False, action="store_true")
parser.add_argument("--news", "-n", default=None, required=False, help="Add google news country code eg. \"us\"")

args = parser.parse_args()


@contextmanager
def setlocale(name):  # thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


# maps open weather icons to
# icon reading is not impacted by the 'lang' parameter
icon_lookup = {
    "clear": "assets/Sun.png",  # clear sky day
    "clear-night": "assets/Moon.png",  # clear sky night
    "cloudy": "assets/Cloud.png",  # cloudy day
    "error": "assets/exclamation.png",  # something went wrong useful for debugging with get_icon()
    "fog": "assets/Haze.png",  # fog day
    "hail": "assets/Hail.png",  # hail
    "humid": "assets/humid.png",  # humidity % sign
    "mostly cloudy": "assets/Cloud.png",  # cloudy day
    "partly-cloudy-day": "assets/PartlySunny.png",  # partly cloudy day
    "partly-cloudy-night": "assets/PartlyMoon.png",  # scattered clouds night
    "rain": "assets/Rain.png",  # rain day
    "snow": "assets/Snow.png",  # snow day
    "snow-thin": "assets/Snow.png",  # sleet day
    "thunderstorm": "assets/Storm.png",  # thunderstorm
    "tornado": "assets/Tornado.png",  # tornado
    "wind": "assets/Wind.png",  # wind
}


def get_icon(icon_name, x=100, y=100):
    res = None
    image = None
    try:
        # we use casefold because external weather api may return Capitalised or not
        image = Image.open(icon_lookup[icon_name.casefold()])
    except Exception as e:
        print(f"Error: {e}. Cannot get {icon_name}")
        image = Image.open(icon_lookup["error"])

    image = image.resize((x, y), Image.ANTIALIAS)
    image = image.convert("RGB")
    res = ImageTk.PhotoImage(image)

    return res


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black")
        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize day of week
        self.day_of_week1 = ''
        self.dayOWLbl = Label(self, text=self.day_of_week1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dayOWLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dateLbl.pack(side=TOP, anchor=E)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p')  # hour in 12h format
            else:
                time2 = time.strftime('%H:%M')  # hour in 24h format

            day_of_week2 = time.strftime('%A')
            date2 = time.strftime(date_format)
            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if day_of_week2 != self.day_of_week1:
                self.day_of_week1 = day_of_week2
                self.dayOWLbl.config(text=day_of_week2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)
            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
            self.timeLbl.after(200, self.tick)


class Weather(Frame):
    def __init__(self, parent, location, imperial_units=False, *args, **kwargs):
        Frame.__init__(self, parent, bg="black")
        # self.forecast = ""
        self.humid = "%"
        self.location = location
        self.temperature = ""
        self.temp_unit = python_weather.METRIC
        self.temp_unit_str = "℃"
        self.minmax = ""
        self.tempFrame = Frame(self, background="black")
        # current weather icon
        self.current_weather_iconLbl = Label(self.tempFrame, bg="black")
        image = get_icon("error", x=90, y=90)
        self.current_weather_iconLbl.config(image=image)
        self.current_weather_iconLbl.image = image

        if imperial_units:
            self.temp_unit = python_weather.IMPERIAL
            self.temp_unit_str = "℉"

        # get weather from internets
        self.weather_loop = asyncio.get_event_loop()
        self.get_weather()

        # construct display elements
        self.tempFrame.pack(side=TOP, anchor=W, fill=BOTH, expand=True)
        self.tempLbl = Label(self.tempFrame, text=self.temperature, font=("Helvetica", xlarge_text_size), fg="white", bg="black")
        self.tempLbl.pack(side=LEFT, anchor=N)
        self.temp_unitLbl = Label(self.tempFrame, text=self.temp_unit_str, font=("Helvetica", large_text_size), fg="white", bg="black")
        self.temp_unitLbl.pack(side=LEFT, anchor=N)
        self.current_weather_iconLbl.pack(side=LEFT, anchor=N, padx=20)
        self.minmaxLbl = Label(self, text=self.minmax, font=("Helvetica", medium_text_size), fg="white", bg="black")
        self.minmaxLbl.pack(side=TOP, anchor=W)
        # Keeping image inline with text requires a frame to hold both items
        self.humidFrame = Frame(self, background="black")
        self.humidFrame.pack(side=TOP, anchor=W, fill=BOTH, expand=True)
        self.humidLbl = Label(self.humidFrame, text=self.humid, font=("Helvetica", 24), fg="white", bg="black")
        self.humidLbl.pack(side=LEFT, anchor=W)
        self.humid_iconLbl = Label(self.humidFrame, bg="black")
        # 24 pixels seems to be best at 1080p and to line up with humidFrame
        image = get_icon("humid", x=24, y=24)
        self.humid_iconLbl.config(image=image)
        self.humid_iconLbl.image = image
        self.humid_iconLbl.pack(side=LEFT, anchor=W, pady=5)
        self.locationLbl = Label(self, text=self.location, font=("Helvetica", small_text_size), fg="white", bg="black")
        self.locationLbl.pack(side=TOP, anchor=W)

    def __del__(self):
        self.weather_loop.close()

    async def async_get_weather(self):
        client = python_weather.Client(format=self.temp_unit)

        weather = await client.find(self.location)
        self.temperature = str(weather.current.temperature)
        image = get_icon(weather.current.sky_text, x=90, y=90)
        self.current_weather_iconLbl.config(image=image)
        self.current_weather_iconLbl.image = image
        self.humid = str(weather.current.humidity)
        # forecast includes the previous two days so today's "forecast" is the second item
        for forecast in weather.forecasts[2:3]:
            self.minmax = f"{forecast.low}-{forecast.high}"

        await client.close()

    # after() function needs a non async wrapper
    def get_weather(self):
        self.weather_loop.run_until_complete(self.async_get_weather())
        # update every 30 mins
        self.after(1800000, self.get_weather)

    @staticmethod
    def convert_kelvin_to_fahrenheit(kelvin_temp):
        return 1.8 * (kelvin_temp - 273) + 32


class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg="black")
        self.title = "News"  # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title, font=("Helvetica", medium_text_size), fg="white", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if args.news is None:
                headlines_url = "https://news.google.com/news?ned=us&output=rss"
            else:
                headlines_url = f"https://news.google.com/news?ned={args.news}&output=rss"

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:5]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print(f"Error: {e}. Cannot get news.")

        self.after(200000, self.get_headlines)


class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg="black")

        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert("RGB")
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg="black", image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=("Helvetica", xsmall_text_size), fg="white",
                                  bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events'
        self.calendarLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=E)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=E)
        self.get_events()

    def get_events(self):
        # TODO: implement this method
        # reference https://developers.google.com/google-apps/calendar/quickstart/python

        # remove all children
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        calendar_event = CalendarEvent(self.calendarEventContainer)
        calendar_event.pack(side=TOP, anchor=E)
        pass


class CalendarEvent(Frame):
    def __init__(self, parent, event_name="Event 1"):
        Frame.__init__(self, parent, bg='black')
        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white",
                                  bg="black")
        self.eventNameLbl.pack(side=TOP, anchor=E)


class FullScreenWindow:
    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background='black')
        self.bottomFrame = Frame(self.tk, background='black')
        self.topFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.bottomFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
        self.state = False
        self.tk.bind("<Return>", self.toggle_full_screen)
        self.tk.bind("<Escape>", self.destroy_session)
        # clock
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=RIGHT, anchor=N, padx=0, pady=60)
        # weather
        self.weather = Weather(self.topFrame, location=args.location)
        self.weather.pack(side=LEFT, anchor=N, padx=80, pady=60)
        # news
        self.news = News(self.bottomFrame)
        self.news.pack(side=LEFT, anchor=S, padx=5, pady=60)
        # start fullscreen
        self.toggle_full_screen()

    def toggle_full_screen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_full_screen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"

    def destroy_session(self, event=None):
        self.tk.destroy()
        return "break"


if __name__ == '__main__':
    print(f"{args}")
    w = FullScreenWindow()
    w.tk.mainloop()
