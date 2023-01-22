from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import RU, Notice
from .serializers import RUSerializer, NoticeSerializer
from datetime import date, timedelta


class RUView(APIView):
    @method_decorator(cache_page(60))
    def get(self, _):
        ru = RU.objects.all()
        serializer = RUSerializer(ru, many=True)
        return Response(serializer.data)


class NoticeView(APIView):
    @method_decorator(cache_page(60))
    def get(self, _):
        notice = Notice.objects.last()
        if notice:
            serializer = NoticeSerializer(notice, allow_null=True)
            return Response(serializer.data)
        else:
            return Response(False)


def campus_view(request):
    ctx = {
        'campi': [
            {
                'display': RU.ARARAS,
                'url': RU.URL_ARARAS,
            },
            {
                'display': RU.LAGOA_DO_SINO,
                'url': RU.URL_LAGOA_DO_SINO,
            },
            {
                'display': RU.SOROCABA,
                'url': RU.URL_SOROCABA,
            },
            {
                'display': RU.SÃO_CARLOS,
                'url': RU.URL_SÃO_CARLOS,
            },
        ]
    }
    return render(request, "ru/index.html", ctx)


WDS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']


def weekday_correct(time):
    return (time.weekday() + 1) % 7


def meal_opt_dict(meal):
    if meal:
        return {
            'main_dish_unrestricted': meal.main_dish_unrestricted,
            'main_dish_vegetarian': meal.main_dish_vegetarian,
            'main_dish_extra': meal.main_dish_extra,
            'garnish': meal.garnish,
            'accompaniment': meal.accompaniment,
            'salads': meal.salads,
            'dessert': meal.dessert,
            'juice': meal.juice,
        }
    else:
        return {
            'main_dish_unrestricted': 'Não Definido',
            'main_dish_vegetarian': 'Não Definido',
            'main_dish_extra': 'Não Definido',
            'garnish': 'Não Definido',
            'accompaniment': 'Não Definido',
            'salads': 'Não Definido',
            'dessert': 'Não Definido',
            'juice': 'Não Definido',
        }


def menu_view(request, campus):
    today = date.today()
    if weekday_correct(today) == 0:
        sunday = today
    else:
        sunday = today - timedelta(days=weekday_correct(today) % 7 - 7)

    lst = []
    for delta in range(7):
        lunch = RU.objects.filter(
            meal_type=RU.ALMOÇO,
            campus=RU.url_to_campus(campus),
            date=sunday + timedelta(days=delta),
        ).first()

        dinner = RU.objects.filter(
            meal_type=RU.JANTAR,
            campus=RU.url_to_campus(campus),
            date=sunday + timedelta(days=delta),
        ).first()

        lst.append({
            'index': delta,
            'day': (sunday + timedelta(days=delta)).day,
            'weekDay': WDS[delta],
            'lunch': meal_opt_dict(lunch),
            'dinner': meal_opt_dict(dinner),
        })

    ctx = {
        'lst': lst,
        'today': weekday_correct(today),
        'campus': RU.url_to_campus(campus),
    }

    return render(request, "ru/menu.html", ctx)
