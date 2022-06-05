from django.core.management.base import BaseCommand
from django.db import transaction
from html.parser import HTMLParser
from django.db.utils import IntegrityError
from pyppeteer import launch
from PIL import Image, ImageMath
from requests import get
from pkg_resources import resource_stream
from pytesseract import image_to_string

from ru.models import RU
from datetime import date, datetime, timedelta, timezone

import asyncio
import re
import io

MASK = Image.open(resource_stream('ru', 'mask.png')).convert(mode='L')

DATE_PATTERN = '(\d+)\s*/\s*(\d+)'

MEALS = [RU.ALMOÇO, RU.JANTAR]
MEAL_PATTERN = f'({"|".join(MEALS)})'

CAMPUSES = [RU.SÃO_CARLOS, RU.ARARAS, RU.SOROCABA, RU.LAGOA_DO_SINO]
CAMPUS_PATTERN = f'({"|".join(CAMPUSES)})'

BASE_URL = 'https://www.facebook.com'

# URL for the RU's timeline album.
ALBUM_URL = BASE_URL + '/media/set/?set=a.160605075654161'

# Size of the images we expect to be posted.
IMAGE_SIZE = (960, 540)

# Rectangle bounds for where we expect the campus name to be written.
# Bounds are written as (left, upper, right, lower).
CAMPUS_BOUNDS = (281, 10, 679, 70)

# Rectangle bounds for where we expect the date to be written.
DATE_BOUNDS = (281, 81, 679, 140)

# Rectangle bounds for where we expect data to be written.
BOUNDS = [
    (512, 141, 916, 201), # Main dish
    (512, 207, 916, 266), # Vegetarian
    (512, 272, 916, 332), # Garrison
    (512, 338, 916, 397), # Accompaniment
    (512, 403, 916, 462), # Salad
    (512, 469, 916, 528), # Dessert
]

# Dictionary for correcting Tesseract jank on a case-by-case basis.
CORRECTIONS = {
    'Com': 'com',
    'Pts': 'PTS',
    'Ao': 'ao',
    'De': 'de',
    'Do': 'do',
    'Da': 'da',
    'Em': 'em',
    'No': 'no',
    'Na': 'na',
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
        if tag == 'img':
            for attr in attrs:
                if attr[0] == 'src':
                    self.urls.add(attr[1])


class UnrecognizedImageError(Exception):
    pass


def preprocess(img):
    img = img.convert(mode='L')
    img = Image.eval(img, lambda x: (13005 - 51 * x) // 19)
    img = ImageMath.eval('a + b', a=img, b=MASK)
    return img.convert(mode='RGB')


class Meal:
    def __init__(self, img):
        img = preprocess(Image.open(io.BytesIO(img)).resize(IMAGE_SIZE))

        # Recognize the campus.
        campus = image_to_string(img.crop(CAMPUS_BOUNDS), lang='por').lower()
        print(f"campus is {campus}")
        campus_match = re.search(CAMPUS_PATTERN, campus)
        if campus_match == None:
            raise UnrecognizedImageError

        # Recognize the date.
        datestr = image_to_string(img.crop(DATE_BOUNDS), lang='por').lower()
        print(datestr)
        date_match = re.search(DATE_PATTERN, datestr)
        meal_match = re.search(MEAL_PATTERN, datestr)
        if date_match == None or meal_match == None:
            raise UnrecognizedImageError

        try:
            self.campus = campus_match.group(1)
            self.day = int(date_match.group(1))
            self.month = int(date_match.group(2))
            self.meal = meal_match.group(1)
        except ValueError as _:
            raise UnrecognizedImageError

        # Recognize meal data.
        strings = []
        for bound in BOUNDS:
            istr = image_to_string(img.crop(bound), lang='por').lower()
            istr = re.sub('\s+', ' ', istr)
            # Capitalize words and apply corrections.
            out = []
            for word in istr.split():
                word = word.capitalize()
                if CORRECTIONS.get(word):
                    word = CORRECTIONS[word]
                out.append(word)
            strings.append(' '.join(out))

        print(strings)

        self.maindish = strings[0]
        self.vegetarian = strings[1]
        self.garrison = strings[2]
        self.accompaniment = strings[3]
        self.salad = strings[4]
        self.dessert = strings[5]


async def download_image(url):
    r = get(url)
    lm = r.headers.get('last-modified')
    last_modified = datetime.strptime(lm, '%a, %d %b %Y %H:%M:%S %Z')
    last_modified = last_modified.replace(tzinfo=timezone.utc)
    return (r.content, last_modified)


async def browse(until):
    browser = await launch(
        executablePath='google-chrome-stable',
        args=['--no-sandbox'],
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )

    page = await browser.newPage()
    await page.goto(ALBUM_URL, waitUntil='networkidle0')

    remaining_scroll_attempts = 8
    remaining_image_attempts = 8
    viewed_urls = set()
    output = []

    while True:
        # Parse the URLs currently visible.
        parser = AlbumHTMLParser()
        parser.feed(await page.content())

        # No new URLs have appeared.
        # Wait and try some more times.
        if parser.urls.issubset(viewed_urls):
            remaining_scroll_attempts -= 1
            print(f"{remaining_scroll_attempts} attempts remaining.")
            await page.waitFor(10_000)
            if remaining_scroll_attempts == 0:
                await browser.close()
                return output
        else:
            remaining_scroll_attempts = 8

        # Scroll to the bottom.
        imgs = await page.JJ('img')
        await imgs[-1].hover()

        for url in parser.urls - viewed_urls:
            await page.waitFor(10_000)
            print(url)
            img, last_modified = await download_image(url)
            print(last_modified)

            # Reached a post that is older than requested.
            # Try skipping it, give up if more than 8 appear in a row.
            if last_modified < until:
                remaining_image_attempts -= 1
                if remaining_image_attempts == 0:
                    await browser.close()
                    return output
            else:
                remaining_image_attempts = 8

            try:
                output.append(Meal(img))
            except UnrecognizedImageError as _:
                continue

        # Add parsed URLs to the viewed list.
        viewed_urls = viewed_urls.union(parser.urls)


@transaction.atomic
def store_meals(meals):
    # Store atomically so that we can catch posts more reliably.
    for meal in meals:
        print(f"--- {meal.campus} ~ {meal.day}/{meal.month} ~ {meal.meal} ---")
        print("Prato Principal:", meal.maindish)
        print("Vegetariano:", meal.vegetarian)
        print("Guarnição:", meal.garrison)
        print("Acompanhamento:", meal.accompaniment)
        print("Salada:", meal.salad)
        print("Sobremesa:", meal.dessert)

        # FIXME Doesn't work near Jan 1st.
        year = datetime.now().year
        try:
            RU.objects.create(
                date=datetime(year=year, month=meal.month, day=meal.day),
                campus=meal.campus,
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


class Command(BaseCommand):
    help = "Updates the RU database."

    def handle(self, *args, **options):
        # Prune objects older than a week, but keep at least 1.
        count = RU.objects.count()
        for obj in RU.objects.all():
            age = obj.date - date.today()
            if age.days > 7 and count > 1:
                obj.delete()
                count = count - 1

        # Look for posts younger than the last time we checked. Or one week old
        # if the DB is empty.
        until = None
        if count > 0:
            until = RU.objects.latest('created_at').created_at
        else:
            until = datetime.now(tz=timezone.utc) - timedelta(weeks=1)

        store_meals(asyncio.new_event_loop().run_until_complete(browse(until)))
