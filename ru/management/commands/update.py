from django.core.management.base import BaseCommand
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

BASE_URL = 'https://www.facebook.com'

# URL for the RU's timeline album.
ALBUM_URL = BASE_URL + '/media/set/?set=a.160605075654161'

# Size of the images we expect to be posted.
IMAGE_SIZE = (960, 540)

# Rectangle bounds for where we expect the date to be written.
# Bounds are written as (left, upper, right, lower).
DATE_BOUNDS = (254, 72, 690, 108)

# Rectangle bounds for where we expect data to be written.
MAIN_DISH_BOUNDS     = (520, 126, 910, 162)
VEGETARIAN_BOUNDS    = (520, 177, 910, 214)
EXTRA_BOUNDS         = (520, 229, 910, 265)
GARNISH_BOUNDS       = (520, 280, 910, 316)
SALAD_BOUNDS         = (520, 331, 910, 367)
ACCOMPANIMENT_BOUNDS = (520, 383, 910, 419)
DESSERT_BOUNDS       = (520, 434, 910, 470)
JUICE_BOUNDS         = (520, 485, 910, 521)

# Dictionary for correcting Tesseract jank on a case-by-case basis.
CORRECTIONS = {
    'C/': 'c/',
    'Com': 'com',
    'Pts': 'PTS',
    'De': 'de',
    'Do': 'do',
    'Da': 'da',
    'Em': 'em',
    'No': 'no',
    'Na': 'na',
    'Ou': 'ou',
    'A': 'a',
    'Ao': 'ao',
    'À': 'à',
    'Á': 'á',
    'E': 'e',
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


def read_img(img, bounds):
    text = image_to_string(img.crop(bounds), lang='por')
    text = text.lower()
    text = re.sub('\s+', ' ', text)
    out = []
    for word in text.split():
        word = word.capitalize()
        if CORRECTIONS.get(word):
            word = CORRECTIONS[word]
        out.append(word)
    return ' '.join(out)

class Meal:
    def __init__(self, img):
        img = preprocess(Image.open(io.BytesIO(img)).resize(IMAGE_SIZE))

        # Recognize the date.
        datestr = read_img(img, DATE_BOUNDS)
        date_match = re.search(DATE_PATTERN, datestr)
        meal_match = re.search(MEAL_PATTERN, datestr)
        if date_match == None or meal_match == None:
            raise UnrecognizedImageError

        try:
            self.day = int(date_match.group(1))
            self.month = int(date_match.group(2))
            self.meal_type = meal_match.group(1)
        except ValueError as _:
            raise UnrecognizedImageError

        # Recognize meal data.
        self.main_dish_unrestricted = read_img(img, MAIN_DISH_BOUNDS)
        self.main_dish_vegetarian = read_img(img, VEGETARIAN_BOUNDS)
        self.main_dish_extra = read_img(img, EXTRA_BOUNDS)
        self.garnish = read_img(img, GARNISH_BOUNDS)
        self.accompaniment = read_img(img, ACCOMPANIMENT_BOUNDS)
        self.salads = read_img(img, SALAD_BOUNDS)
        self.dessert = read_img(img, DESSERT_BOUNDS)
        self.juice = read_img(img,JUICE_BOUNDS)

    def display(self):
        print(f"{self.day}/{self.month} ~ {self.meal_type}")
        print("\tPrato Principal sem Restrição:", self.main_dish_unrestricted)
        print("\tPrato Principal Vegetariano:", self.main_dish_vegetarian)
        print("\tPrato Principal Extra:", self.main_dish_extra)
        print("\tGuarnição:", self.garnish)
        print("\tAcompanhamento:", self.accompaniment)
        print("\tSaladas:", self.salads)
        print("\tSobremesa:", self.dessert)
        print("\tSuco:", self.juice)


async def download_image(url):
    r = get(url)
    lm = r.headers.get('last-modified')
    last_modified = datetime.strptime(lm, '%a, %d %b %Y %H:%M:%S %Z')
    last_modified = last_modified.replace(tzinfo=timezone.utc)
    return (r.content, last_modified)


async def browse(page, until):
    await page.goto(ALBUM_URL, waitUntil='networkidle0')

    remaining_scroll_attempts = 8
    remaining_image_attempts = 8
    remaining_text_attempts = 8
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
            print(f"SCROLL: {remaining_scroll_attempts} attempts remaining.")
            await page.waitFor(10_000)
            if remaining_scroll_attempts == 0:
                return output
        else:
            remaining_scroll_attempts = 8

        # Scroll to the bottom.
        imgs = await page.JJ('img')
        await imgs[-1].hover()

        for url in parser.urls - viewed_urls:
            await page.waitFor(10_000)
            img, last_modified = await download_image(url)

            # Reached a post that is older than requested.
            # Try skipping it, give up if more than 8 appear in a row.
            if last_modified < until:
                remaining_image_attempts -= 1
                print(f"IMG: {remaining_image_attempts} attempts remaining.")
                if remaining_image_attempts == 0:
                    return output
            else:
                remaining_image_attempts = 8

            try:
                meal = Meal(img)
                meal.display()
                output.append(meal)
                remaining_text_attempts = 8
            except UnrecognizedImageError as _:
                remaining_text_attempts -= 1
                print(f"TEXT: {remaining_text_attempts} attempts remaining.")
                if remaining_text_attempts == 0:
                    return output

        # Add parsed URLs to the viewed list.
        viewed_urls = viewed_urls.union(parser.urls)


async def get_meals(until):
    browser = await launch(
        executablePath='google-chrome-stable',
        args=['--no-sandbox'],
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )

    try:
        return await browse(await browser.newPage(), until)
    finally:
        await browser.close()


def nearest_date(month, day):
    current_year = datetime.now().year
    dates = []
    for year in [current_year - 1, current_year, current_year + 1]:
        date = datetime(year, month, day)
        dates.append((abs(datetime.now() - date), date))
    return min(dates)[1]


def store_meals(meals):
    for meal in meals:
        for campus in CAMPUSES:
            try:
                RU.objects.create(
                    date=nearest_date(meal.month, meal.day),
                    campus=campus,
                    meal_type=meal.meal_type,
                    main_dish_unrestricted=meal.main_dish_unrestricted,
                    main_dish_vegetarian=meal.main_dish_vegetarian,
                    main_dish_extra=meal.main_dish_extra,
                    garnish=meal.garnish,
                    accompaniment=meal.accompaniment,
                    salads=meal.salads,
                    dessert=meal.dessert,
                    juice=meal.juice,
                )
            except IntegrityError as _:
                continue


class Command(BaseCommand):
    help = "Updates the RU database."

    def handle(self, *args, **options):
        print("Begin update")

        # Prune objects older than a week, but keep at least 1.
        count = RU.objects.count()
        for obj in RU.objects.all():
            age = date.today() - obj.date
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

        meals = asyncio.new_event_loop().run_until_complete(get_meals(until))
        store_meals(meals)

        print("Update success")
