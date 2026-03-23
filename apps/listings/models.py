from django.conf import settings
from django.db import models


class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'regions'
        ordering = ['name']

    def __str__(self):
        return self.name


class Listing(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('needs_edit', 'Needs Edit'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('EUR', 'EUR'),
        ('UAH', 'UAH'),
    ]

    ENGINE_TYPE_CHOICES = [
        ('gasoline', 'Gasoline'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('lpg', 'LPG'),
    ]

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    car_brand = models.ForeignKey('cars.CarBrand', on_delete=models.CASCADE, related_name='listings')
    car_model = models.ForeignKey('cars.CarModel', on_delete=models.CASCADE, related_name='listings')
    year = models.IntegerField()
    description = models.TextField()
    original_price = models.DecimalField(max_digits=12, decimal_places=2)
    original_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_eur = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_uah = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rate_usd_uah = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    rate_eur_uah = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    rate_date = models.DateTimeField(null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='listings')
    city = models.CharField(max_length=100)
    mileage = models.IntegerField(default=0)
    engine_type = models.CharField(max_length=20, choices=ENGINE_TYPE_CHOICES, default='gasoline')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    edit_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'listings'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.car_brand} {self.car_model} ({self.year}) - {self.original_price} {self.original_currency}'


