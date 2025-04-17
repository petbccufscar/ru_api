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

def postprocess(text):
    text = text.lower()
    text = re.sub('\s+', ' ', text)
    out = []
    for word in text.split():
        word = word.capitalize()
        if CORRECTIONS.get(word):
            word = CORRECTIONS[word]
        out.append(word)
    return ' '.join(out)

def get_meals():
    out = []
    response = get(MENU_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    content_core = soup.find(id='content-core')
    
    cardapio_text = content_core.get_text()
    cardapio_start = cardapio_text.find("CARDÁPIO")
    
    if cardapio_start == -1:
        return []
    
    cardapio_text = cardapio_text[cardapio_start:]
    
    date_matches = re.finditer(r'([A-ZÇ]+-FEIRA|S[ÁA]BADO|DOMINGO)\s+-\s+(\d{2}/\d{2})', cardapio_text)
    
    date_positions = []
    for match in date_matches:
        date_positions.append((match.start(), match.group()))
    
    day_sections = []
    for i, (pos, date_str) in enumerate(date_positions):
        start = pos
        if i < len(date_positions) - 1:
            end = date_positions[i+1][0]
            day_sections.append((date_str, cardapio_text[start:end]))
        else:
            day_sections.append((date_str, cardapio_text[start:]))
    
    for date_str, day_section in day_sections:
        date_match = re.search(r'.*\s+-\s+(\d{2})/(\d{2})', date_str)
        if not date_match:
            continue
            
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        
        alm_idx = day_section.find("ALMOÇO")
        jan_idx = day_section.find("JANTAR")
        
        if alm_idx != -1 and jan_idx != -1:
            lunch_text = day_section[alm_idx:jan_idx]
            dinner_text = day_section[jan_idx:]
        elif alm_idx != -1:
            lunch_text = day_section[alm_idx:]
            dinner_text = ""
        elif jan_idx != -1:
            lunch_text = ""
            dinner_text = day_section[jan_idx:]
        else:
            continue
        
        if lunch_text:
            lunch = Meal()
            lunch.day = day
            lunch.month = month
            lunch.meal_type = RU.ALMOÇO
            
            unrestricted = re.search(r'PRATO PRINCIPAL.*SEM RESTRIÇÃO:?\s*(.*?)(?=PRATO PRINCIPAL|GUARNIÇÃO|$)', 
                               lunch_text, re.DOTALL | re.IGNORECASE)
            if unrestricted:
                lunch.main_dish_unrestricted = postprocess(unrestricted.group(1))
            
            vegetarian = re.search(r'PRATO PRINCIPAL.*VEGETARIANO:?\s*(.*?)(?=PRATO PRINCIPAL|GUARNIÇÃO|$)', 
                             lunch_text, re.DOTALL | re.IGNORECASE)
            if vegetarian:
                lunch.main_dish_vegetarian = postprocess(vegetarian.group(1))
            
            extra = re.search(r'PRATO PRINCIPAL.*EXTRA:?\s*(.*?)(?=GUARNIÇÃO|$)', 
                        lunch_text, re.DOTALL | re.IGNORECASE)
            if extra:
                lunch.main_dish_extra = postprocess(extra.group(1))
            
            garnish = re.search(r'GUARNIÇÃO:?\s*(.*?)(?=ACOMPANHAMENTOS|$)', lunch_text, re.DOTALL | re.IGNORECASE)
            if garnish:
                lunch.garnish = postprocess(garnish.group(1))
            
            accompaniment = re.search(r'ACOMPANHAMENTOS:?\s*(.*?)(?=SALADA|$)', lunch_text, re.DOTALL | re.IGNORECASE)
            if accompaniment:
                lunch.accompaniment = postprocess(accompaniment.group(1))
            
            salads = re.search(r'SALADA/SOPA:?\s*(.*?)(?=SOBREMESA|$)', lunch_text, re.DOTALL | re.IGNORECASE)
            if salads:
                lunch.salads = postprocess(salads.group(1))
            
            dessert = re.search(r'SOBREMESA:?\s*(.*?)(?=\n\s*\n|$)', lunch_text, re.DOTALL | re.IGNORECASE)
            if dessert:
                lunch.dessert = postprocess(dessert.group(1))
            
            out.append(lunch)
            
        if dinner_text:
            dinner = Meal()
            dinner.day = day
            dinner.month = month
            dinner.meal_type = RU.JANTAR
            
            unrestricted = re.search(r'PRATO PRINCIPAL.*SEM RESTRIÇÃO:?\s*(.*?)(?=PRATO PRINCIPAL|GUARNIÇÃO|$)', 
                               dinner_text, re.DOTALL | re.IGNORECASE)
            if unrestricted:
                dinner.main_dish_unrestricted = postprocess(unrestricted.group(1))
            
            vegetarian = re.search(r'PRATO PRINCIPAL.*VEGETARIANO:?\s*(.*?)(?=PRATO PRINCIPAL|GUARNIÇÃO|$)', 
                             dinner_text, re.DOTALL | re.IGNORECASE)
            if vegetarian:
                dinner.main_dish_vegetarian = postprocess(vegetarian.group(1))
            
            extra = re.search(r'PRATO PRINCIPAL.*EXTRA:?\s*(.*?)(?=GUARNIÇÃO|$)', 
                        dinner_text, re.DOTALL | re.IGNORECASE)
            if extra:
                dinner.main_dish_extra = postprocess(extra.group(1))
            
            garnish = re.search(r'GUARNIÇÃO:?\s*(.*?)(?=ACOMPANHAMENTOS|$)', dinner_text, re.DOTALL | re.IGNORECASE)
            if garnish:
                dinner.garnish = postprocess(garnish.group(1))
            
            accompaniment = re.search(r'ACOMPANHAMENTOS:?\s*(.*?)(?=SALADA|$)', dinner_text, re.DOTALL | re.IGNORECASE)
            if accompaniment:
                dinner.accompaniment = postprocess(accompaniment.group(1))
            
            salads = re.search(r'SALADA/SOPA:?\s*(.*?)(?=SOBREMESA|$)', dinner_text, re.DOTALL | re.IGNORECASE)
            if salads:
                dinner.salads = postprocess(salads.group(1))
            
            dessert = re.search(r'SOBREMESA:?\s*(.*?)(?=\n\s*\n|$)', dinner_text, re.DOTALL | re.IGNORECASE)
            if dessert:
                dinner.dessert = postprocess(dessert.group(1))
            
            out.append(dinner)
    
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