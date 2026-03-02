from django.db import models


class Permission(models.Model):
    codename = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permissions'

    def __str__(self):
        return self.codename


class Role(models.Model):
    SCOPE_CHOICES = [
        ('platform', 'Platform'),
        ('dealership', 'Dealership'),
    ]

    name = models.CharField(max_length=50)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='platform')
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')

    class Meta:
        db_table = 'roles'
        unique_together = ('name', 'scope')

    def __str__(self):
        return f'{self.name} ({self.scope})'
