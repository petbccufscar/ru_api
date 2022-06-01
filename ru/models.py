from django.db import models


class RU(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    lunch = models.CharField(default='Almoço', max_length=100)
    date = models.DateField()
    mainMeal = models.CharField(default='Não definido', max_length=100)
    mainMealVegetarian = models.CharField(default='Não definido', max_length=100)
    garrison = models.CharField(default='Não definido', max_length=100)
    accompaniment = models.CharField(default='Não definido', max_length=100)
    salad = models.CharField(default='Não definido', max_length=100)
    dessert = models.CharField(default='Não definido', max_length=100)

