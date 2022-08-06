from urllib import request
from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from PIL import Image, ImageMath, UnidentifiedImageError
from requests import get
from pkg_resources import resource_stream
from bs4 import BeautifulSoup
from pytesseract import image_to_string

from ru.models import RU
from datetime import date, datetime, timedelta, timezone

import re
import io

MASK = Image.open(resource_stream('ru', 'mask.png')).convert(mode='L')

DATE_PATTERN = re.compile('(\d+)\s*/\s*(\d+)')

MEALS = [RU.ALMOÇO, RU.JANTAR]
MEAL_PATTERN = re.compile(f'({"|".join(MEALS)})')

CAMPUSES = [RU.SÃO_CARLOS, RU.ARARAS, RU.SOROCABA, RU.LAGOA_DO_SINO]

MENU_URL = (
    'https://www.proad.ufscar.br/pt-br/servicos/restaurante-universitario'
)

# Size of the images we expect to be posted.
MAIN_IMAGE_SIZE = (1920, 1080)

# Rectangle bounds for the two sub-images to crop.
# Bounds are written as (left, upper, right, lower).
SUBL_BOUNDS = (  64, 132,  914, 1054)
SUBR_BOUNDS = (1004, 132, 1854, 1054)

# Rectangle bounds for where we expect the date to be written.
DATE_BOUNDS = (15, 15, 831, 108)

# Rectangle bounds for where we expect data to be written.
MAIN_DISH_BOUNDS     = (429, 106, 826, 201)
VEGETARIAN_BOUNDS    = (429, 201, 826, 301)
EXTRA_BOUNDS         = (429, 301, 826, 407)
GARNISH_BOUNDS       = (429, 407, 826, 509)
SALAD_BOUNDS         = (429, 509, 826, 614)
ACCOMPANIMENT_BOUNDS = (429, 614, 826, 715)
DESSERT_BOUNDS       = (429, 715, 826, 821)
JUICE_BOUNDS         = (429, 821, 826, 918)

# Dictionary for correcting Tesseract jank on a case-by-case basis.
CORRECTIONS = {
    'C/': 'c/',
    'Com': 'com',
    'Pts': 'PTS',
    'De': 'de',
    'Do': 'do',
    'Da': 'da',
    'Em': 'em',
    'Fejão': 'Feijão',
    'No': 'no',
    'Na': 'na',
    'Ou': 'ou',
    'A': 'a',
    'Ao': 'ao',
    'À': 'à',
    'Á': 'á',
    'E': 'e',
}


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


def get_meals():
    out = []
    soup = BeautifulSoup(get(MENU_URL).text, 'html.parser')
    for img in soup.find_all('img'):
        print(img['src'].split('/@@')[0])
        content = get(img['src'].split('/@@')[0]).content
        try:
            image = Image.open(io.BytesIO(content)).resize(MAIN_IMAGE_SIZE)
        except UnidentifiedImageError:
            continue
        try:
            meal = Meal(preprocess(image.crop(SUBL_BOUNDS)))
            meal.display()
            out.append(meal)
        except UnrecognizedImageError:
            print("fail")
        try:
            meal = Meal(preprocess(image.crop(SUBR_BOUNDS)))
            meal.display()
            out.append(meal)
        except UnrecognizedImageError:
            print("fail")
    return out


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
            date = nearest_date(meal.month, meal.day)

            RU.objects.filter(
                date=date,
                campus=campus,
                meal_type=meal.meal_type
            ).delete()

            RU.objects.create(
                date=date,
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


class Command(BaseCommand):
    help = "Updates the RU database."

    def handle(self, *args, **options):
        print("Begin update")

        # Prune objects older than a week.
        for obj in RU.objects.all():
            age = date.today() - obj.date
            if age.days > 7:
                obj.delete()

        store_meals(get_meals())

        print("Update success")
