from django.db import models


class CurrencyRate(models.Model):
    ccy = models.CharField(max_length=3)  # USD, EUR
    base_ccy = models.CharField(max_length=3, default='UAH')
    buy = models.DecimalField(max_digits=12, decimal_places=4)
    sale = models.DecimalField(max_digits=12, decimal_places=4)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'currency_rates'
        ordering = ['-fetched_at']

    def __str__(self):
        return f'{self.ccy}/{self.base_ccy} sale={self.sale} ({self.fetched_at})'
