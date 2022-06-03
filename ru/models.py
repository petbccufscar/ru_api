from django.db import models


class RU(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    ALMOÇO = 'almoço'
    JANTAR = 'jantar'
    lunch = models.CharField(
        choices=[(ALMOÇO, ALMOÇO), (JANTAR, JANTAR)],
        default=ALMOÇO,
        max_length=6,
    )
    date = models.DateField()
    mainMeal = models.CharField(default='Não definido', max_length=100)
    mainMealVegetarian = models.CharField(default='Não definido', max_length=100)
    garrison = models.CharField(default='Não definido', max_length=100)
    accompaniment = models.CharField(default='Não definido', max_length=100)
    salad = models.CharField(default='Não definido', max_length=100)
    dessert = models.CharField(default='Não definido', max_length=100)
    class Meta:
        constraints = [
            models.UniqueConstraint('date', 'lunch', name='unique_date_lunch')
        ]
