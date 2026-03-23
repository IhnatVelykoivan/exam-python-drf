from django.conf import settings
from django.db import models


class Dealership(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='dealerships/', blank=True, null=True)
    address = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_dealerships')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dealerships'

    def __str__(self):
        return self.name


class DealershipMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dealership_memberships')
    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, related_name='members')
    role = models.ForeignKey('roles.Role', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dealership_memberships'
        unique_together = ('user', 'dealership')

    def __str__(self):
        return f'{self.user.email} @ {self.dealership.name}'
