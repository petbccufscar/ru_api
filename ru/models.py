from django.db import models


class RU(models.Model):
    def __str__(self):
        return f'{self.date} {self.meal_type} {self.campus}'

    ALMOÇO = 'Almoço'
    JANTAR = 'Jantar'
    meal_type = models.CharField(
        choices=[(ALMOÇO, ALMOÇO), (JANTAR, JANTAR)],
        default=ALMOÇO,
        max_length=6,
    )

    URL_SÃO_CARLOS = 'sao_carlos'
    URL_ARARAS = 'araras'
    URL_SOROCABA = 'sorocaba'
    URL_LAGOA_DO_SINO = 'lagoa_do_sino'

    def url_to_campus(url_campus):
        if url_campus == RU.URL_SÃO_CARLOS:
            return RU.SÃO_CARLOS
        elif url_campus == RU.URL_ARARAS:
            return RU.ARARAS
        elif url_campus == RU.URL_SOROCABA:
            return RU.SOROCABA
        elif url_campus == RU.URL_LAGOA_DO_SINO:
            return RU.LAGOA_DO_SINO

    SÃO_CARLOS = 'São Carlos'
    ARARAS = 'Araras'
    SOROCABA = 'Sorocaba'
    LAGOA_DO_SINO = 'Lagoa do Sino'
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

    main_dish_unrestricted = models.CharField(default='', max_length=100)
    main_dish_vegetarian = models.CharField(default='', max_length=100)
    main_dish_extra = models.CharField(default='', max_length=100)
    garnish = models.CharField(default='', max_length=100)
    accompaniment = models.CharField(default='', max_length=100)
    salads = models.CharField(default='', max_length=100)
    dessert = models.CharField(default='', max_length=100)
    juice = models.CharField(default='', max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                'date',
                'meal_type',
                'campus',
                name='unique_date_type_campus',
            )
        ]


class Notice(models.Model):
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    content = models.TextField()
