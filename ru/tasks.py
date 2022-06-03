from threading import Thread
from time import sleep
from html.parser import HTMLParser
from django.db.utils import IntegrityError
from pyppeteer import launch
from PIL import Image

from .models import RU
from datetime import date, datetime, timedelta

import pytesseract
import asyncio
import string
import re
import io

BASE_URL = 'https://www.facebook.com'

# URL for the RU's timeline album.
ALBUM_URL = BASE_URL + '/media/set/?set=a.160605075654161'

# Set of first posts in the RU's timeline.
# For checking if we've reached the bottom of the timeline accidentally.
# Shouldn't be a problem once there are enough posts.
FIRST_URLS = set([
    'https://www.facebook.com/RU.UFSCar/photos/a.160605075654161/488231472891518',
    'https://www.facebook.com/RU.UFSCar/photos/a.160605075654161/457563022625030',
    'https://www.facebook.com/RU.UFSCar/photos/a.160605075654161/457562902625042',
    'https://www.facebook.com/RU.UFSCar/photos/a.160605075654161/488231476224851',
])

# Size of the images we expect to be posted.
IMAGE_SIZE = (1280, 720)

# Rectangle bounds for where we expect the date to be written.
DATE_BOUNDS = (393, 41, 893, 102)

# Rectangle bounds for where we expect the meal to be written.
MEAL_BOUNDS = (442, 106, 838, 163)

# Rectangle bounds for where we expect data to be written.
BOUNDS = [
    (440, 209, 1021, 260), # Main dish
    (440, 293, 1021, 344), # Vegetarian
    (440, 375, 1021, 426), # Garrison
    (440, 459, 1021, 510), # Accompaniment
    (440, 541, 1021, 592), # Salad
    (440, 625, 1021, 676), # Dessert
]

# Dictionary for correcting Tesseract jank on a case-by-case basis.
CORRECTIONS = {
    'Fejão': 'Feijão',
    'Com': 'com',
    'Pts': 'PTS',
    'Ao': 'ao',
    'De': 'de',
    'Em': 'em',
    'Ou': 'ou',
    'E': 'e',
    'Á': 'á',
    'À': 'à',
}


class AlbumHTMLParser(HTMLParser):
    def __init__(self):
        self.urls = set()
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            url = [attr for attr in attrs if attr[0] == 'href'][0][1]
            if re.match('^/RU.UFSCar/photos/.+', url):
                self.urls.add(BASE_URL + url)


class PhotoHTMLParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            src = [attr for attr in attrs if attr[0] == 'src'][0][1]
            if re.match('^https://scontent\..*\.fbcdn\.net/', src):
                self.src = src


class UnrecognizedImageError(Exception):
    pass


class Meal:
    def __init__(self, image_bytes):
        img = Image.open(io.BytesIO(image_bytes))

        if img.size != IMAGE_SIZE:
            raise UnrecognizedImageError

        # Recognize the date.
        date = pytesseract.image_to_string(img.crop(DATE_BOUNDS), lang='por')
        match = re.match('(\d+)\s*/\s*(\d+)', date)

        if match == None:
            raise UnrecognizedImageError

        try:
            day, month = match.groups()
            self.day = int(day)
            self.month = int(month)
        except ValueError as _:
            raise UnrecognizedImageError

        # Recognize the meal type.
        meal = pytesseract.image_to_string(img.crop(MEAL_BOUNDS), lang='por')
        meal = meal.strip().lower()
        if meal in ['almoço', 'jantar']:
            self.meal = meal
        else:
            raise UnrecognizedImageError

        # Recognize meal data.
        strings = []
        for bound in BOUNDS:
            istr = pytesseract.image_to_string(img.crop(bound), lang='por')
            istr = istr.strip().lower()
            space = lambda x: f'{x.group(1)} {x.group(2)}'
            istr = re.sub('([^0-9 ])([0-9]+)', space, istr)
            istr = re.sub('([0-9]+)([^0-9 ])', space, istr)
            out = []
            for word in istr.split():
                word = word.capitalize()
                if CORRECTIONS.get(word):
                    word = CORRECTIONS[word]
                out.append(word)
            strings.append(' '.join(out))

        self.maindish = strings[0]
        self.vegetarian = strings[1]
        self.garrison = strings[2]
        self.accompaniment = strings[3]
        self.salad = strings[4]
        self.dessert = strings[5]


async def download_image(browser, url):
    page = await browser.newPage()
    await page.setViewport({ 'width': 1280, 'height': 720 })
    await page.goto(url, waitUntil='networkidle0')
    parser = PhotoHTMLParser()
    parser.feed(await page.content())
    await page.goto(parser.src)
    result = await page.screenshot()
    await page.close()
    return result


async def browse(desired_dates, patience):
    browser = await launch(
        executablePath='google-chrome-stable',
        args=['--no-sandbox'],
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )

    page = await browser.newPage()
    await page.goto(ALBUM_URL, waitUntil='networkidle0')

    viewed_urls = set()
    viewed_dates = set()
    attempts = 0
    output = []

    while True:
        # Parse the URLs currently visible.
        parser = AlbumHTMLParser()
        parser.feed(await page.content())

        # Scroll to the bottom.
        imgs = await page.JJ('img')
        await imgs[-1].hover()
        await page.waitFor(500)

        for url in parser.urls - viewed_urls:
            print(url)

            attempts = attempts + 1
            if attempts > patience:
                await browser.close()
                return output

            try:
                meal = Meal(await download_image(browser, url))
                date = (meal.month, meal.day, meal.meal)
                if date in desired_dates:
                    attempts = 0
                    output.append(meal)
                    viewed_dates.add(date)
                    if viewed_dates == desired_dates:
                        await browser.close()
                        return output
            except UnrecognizedImageError as _:
                continue

        # Add parsed URLs to the viewed list.
        viewed_urls = viewed_urls.union(parser.urls)

        # Heuristically check if we've reached the bottom of the timeline.
        if not parser.urls.isdisjoint(FIRST_URLS):
            await browser.close()
            return output


def run():
    for obj in RU.objects.all():
        age = obj.date - date.today()
        if age.days > 7:
            obj.delete()

    date_dict = {}
    dates = set()
    for i in range(-7, 8):
        date_ = date.today() + timedelta(days=i)
        dates.add((date_.month, date_.day, 'almoço'))
        date_dict[(date_.month, date_.day, 'almoço')] = date_
        dates.add((date_.month, date_.day, 'jantar'))
        date_dict[(date_.month, date_.day, 'jantar')] = date_

    meals = asyncio.new_event_loop().run_until_complete(browse(dates, 3))

    for meal in meals:
        print(f"--- {meal.day}/{meal.month} {meal.meal} ---")
        print("Prato Principal:", meal.maindish)
        print("Vegetariano:", meal.vegetarian)
        print("Guarnição:", meal.garrison)
        print("Acompanhamento:", meal.accompaniment)
        print("Salada:", meal.salad)
        print("Sobremesa:", meal.dessert)

        try:
            RU.objects.create(
                date=date_dict[(meal.month, meal.day, meal.meal)],
                lunch=meal.meal,
                mainMeal=meal.maindish,
                mainMealVegetarian=meal.vegetarian,
                garrison=meal.garrison,
                accompaniment=meal.accompaniment,
                salad=meal.salad,
                dessert=meal.dessert,
            )
        except IntegrityError as _:
            continue
