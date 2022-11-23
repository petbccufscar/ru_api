from django.core.management.base import BaseCommand
from requests import get
from bs4 import BeautifulSoup
import re

from ru.models import RU
from datetime import date, datetime


MEALS = [RU.ALMOÇO, RU.JANTAR]
CAMPI = [RU.SÃO_CARLOS, RU.ARARAS, RU.SOROCABA, RU.LAGOA_DO_SINO]

MENU_URL = (
    'https://www.proad.ufscar.br/pt-br/servicos/restaurante-universitario'
)


class Meal:
    day = date.today().day
    month = date.today().month
    meal_type = RU.ALMOÇO
    campi = CAMPI
    main_dish_unrestricted = 'Não Definido'
    main_dish_vegetarian = 'Não Definido'
    main_dish_extra = 'Não Definido'
    garnish = 'Não Definido'
    accompaniment = 'Não Definido'
    salads = 'Não Definido'
    dessert = 'Não Definido'
    juice = 'Não Definido'

    def setCampi(self, title: str):
        result = []
        for campus in CAMPI:
            if campus.lower() in title.lower():
                result.append(campus)

        if len(result) == 0:
            result = CAMPI

        self.campi = result

    def display(self):
        print(f"{self.day}/{self.month} ~ {self.meal_type}")
        print('\tCampi:', ", ".join(self.campi))
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
    ps = soup.find(id='content-core').find_all('p')
    while not re.match('cardápio', ps[0].text, flags=re.I):
        ps.pop(0)

    state = None
    meal = Meal()
    for p in ps:
        if match := re.search('restrição.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.main_dish_unrestricted = match[1]
        elif match := re.search('vegetariano.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.main_dish_vegetarian = match[1]
        elif match := re.search('extra.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.main_dish_extra = match[1]
        elif match := re.search('guarniç.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.garnish = match[1]
        elif match := re.search('acompanhamento.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.accompaniment = match[1]
        elif match := re.search('salada.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.salads = match[1]
        elif match := re.search('sobremesa.*:\s*(.*)', p.text, flags=re.I):
            state = 'data'
            meal.dessert = match[1]
        elif match := re.search('(\d+)\s*\/\s*(\d+)', p.text):
            if state == 'data':
                new_meal = Meal()
                new_meal.campi = meal.campi
                new_meal.meal_type = meal.meal_type
                out.append(meal)
                meal = new_meal
            state = 'meta'
            meal.day = int(match[1])
            meal.month = int(match[2])
        elif re.search('almoço', p.text, flags=re.I):
            if state == 'data':
                new_meal = Meal()
                new_meal.day = meal.day
                new_meal.month = meal.month
                new_meal.campi = meal.campi
                out.append(meal)
                meal = new_meal
            state = 'meta'
            meal.meal_type = RU.ALMOÇO
        elif re.search('jantar', p.text, flags=re.I):
            if state == 'data':
                new_meal = Meal()
                new_meal.day = meal.day
                new_meal.month = meal.month
                new_meal.campi = meal.campi
                out.append(meal)
                meal = new_meal
            state = 'meta'
            meal.meal_type = RU.JANTAR
        elif re.search('são\s*carlos|araras|sorocaba|lagoa\s*do\s*sino', p.text, flags=re.I):
            if state == 'data':
                new_meal = Meal()
                new_meal.day = meal.day
                new_meal.month = meal.month
                new_meal.campi = meal.campi
                out.append(meal)
                meal = new_meal
            state = 'meta'
            meal.setCampi(p.text)

    out.append(meal)

    for m in out:
        m.display()

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
        for campus in meal.campi:
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
