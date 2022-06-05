from django.db import models


class RU(models.Model):
    ALMOÇO = 'almoço'
    JANTAR = 'jantar'
    lunch = models.CharField(
        choices=[(ALMOÇO, ALMOÇO), (JANTAR, JANTAR)],
        default=ALMOÇO,
        max_length=6,
    )

    SÃO_CARLOS = 'são carlos'
    ARARAS = 'araras'
    SOROCABA = 'sorocaba'
    LAGOA_DO_SINO = 'lagoa do sino'
    campus = models.CharField(
        choices=[
            (SÃO_CARLOS, SÃO_CARLOS),
            (ARARAS, ARARAS),
            (SOROCABA, SOROCABA),
            (LAGOA_DO_SINO, LAGOA_DO_SINO),
        ],
        default=SÃO_CARLOS,
        max_length=13,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField()
    mainMeal = models.CharField(default='Não definido', max_length=100)
    mainMealVegetarian = models.CharField(default='Não definido', max_length=100)
    garrison = models.CharField(default='Não definido', max_length=100)
    accompaniment = models.CharField(default='Não definido', max_length=100)
    salad = models.CharField(default='Não definido', max_length=100)
    dessert = models.CharField(default='Não definido', max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                'date',
                'lunch',
                'campus',
                name='unique_date_lunch_campus',
            )
        ]
