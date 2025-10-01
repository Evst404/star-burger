from django.db import models
from django.utils import timezone


class Place(models.Model):
    address = models.CharField(
        verbose_name='Адрес',
        max_length=200,
        unique=True,
        db_index=True
    )
    latitude = models.FloatField(
        verbose_name='Широта',
        null=True,
        blank=True
    )
    longitude = models.FloatField(
        verbose_name='Долгота',
        null=True,
        blank=True
    )
    last_updated = models.DateTimeField(
        verbose_name='Дата последнего обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Место'
        verbose_name_plural = 'Места'

    def __str__(self):
        return self.address