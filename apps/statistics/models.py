from django.db import models


class ListingView(models.Model):
    listing = models.ForeignKey(
        'listings.Listing',
        on_delete=models.CASCADE,
        related_name='views',
    )
    viewed_at = models.DateTimeField(auto_now_add=True)
    viewer_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'listing_views'
        ordering = ['-viewed_at']

    def __str__(self):
        return f'View on listing {self.listing_id} at {self.viewed_at}'
