import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.roles.models import Permission, Role

User = get_user_model()

REGIONS = [
    'Вінницька область', 'Волинська область', 'Дніпропетровська область',
    'Донецька область', 'Житомирська область', 'Закарпатська область',
    'Запорізька область', 'Івано-Франківська область', 'Київська область',
    'Кіровоградська область', 'Луганська область', 'Львівська область',
    'Миколаївська область', 'Одеська область', 'Полтавська область',
    'Рівненська область', 'Сумська область', 'Тернопільська область',
    'Харківська область', 'Херсонська область', 'Хмельницька область',
    'Черкаська область', 'Чернівецька область', 'Чернігівська область',
    'Київ',
]

CAR_BRANDS_MODELS = {
    'BMW': ['3 Series', '5 Series', '7 Series', 'X3', 'X5', 'X6'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLE', 'GLS'],
    'Audi': ['A4', 'A6', 'A8', 'Q5', 'Q7'],
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Land Cruiser', 'Prius'],
    'Honda': ['Civic', 'Accord', 'CR-V', 'HR-V'],
    'Volkswagen': ['Golf', 'Passat', 'Tiguan', 'Touareg', 'Jetta'],
    'Hyundai': ['Tucson', 'Santa Fe', 'Sonata', 'Elantra', 'Accent'],
    'Kia': ['Sportage', 'Sorento', 'Cerato', 'Optima', 'Rio'],
    'Nissan': ['Qashqai', 'X-Trail', 'Leaf', 'Juke', 'Rogue'],
    'Ford': ['Focus', 'Fiesta', 'Mustang', 'Explorer', 'Escape'],
    'Chevrolet': ['Cruze', 'Malibu', 'Camaro', 'Tahoe', 'Equinox'],
    'Skoda': ['Octavia', 'Superb', 'Kodiaq', 'Karoq', 'Fabia'],
    'Renault': ['Megane', 'Duster', 'Kadjar', 'Clio', 'Captur'],
    'Mazda': ['3', '6', 'CX-5', 'CX-9', 'MX-5'],
    'Daewoo': ['Lanos', 'Nexia', 'Matiz', 'Sens'],
}

PERMISSIONS = [
    ('can_view_listings', 'View listings', 'Can view car listings'),
    ('can_create_listing', 'Create listing', 'Can create a car listing'),
    ('can_edit_own_listing', 'Edit own listing', 'Can edit own car listing'),
    ('can_delete_own_listing', 'Delete own listing', 'Can delete own car listing'),
    ('can_delete_any_listing', 'Delete any listing', 'Can delete any car listing'),
    ('can_deactivate_listing', 'Deactivate listing', 'Can deactivate a car listing'),
    ('can_ban_user', 'Ban user', 'Can ban a user'),
    ('can_unban_user', 'Unban user', 'Can unban a user'),
    ('can_view_users', 'View users', 'Can view user list'),
    ('can_create_manager', 'Create manager', 'Can create a manager account'),
    ('can_manage_roles', 'Manage roles', 'Can manage roles and permissions'),
    ('can_manage_brands', 'Manage brands', 'Can manage car brands and models'),
    ('can_review_brand_requests', 'Review brand requests', 'Can review brand/model requests'),
    ('can_request_brand', 'Request brand', 'Can request a new brand/model'),
    ('can_view_statistics', 'View statistics', 'Can view listing statistics (Premium)'),
    ('can_manage_dealership', 'Manage dealership', 'Can manage a dealership'),
]

ROLES = {
    'buyer': [
        'can_view_listings',
    ],
    'seller': [
        'can_view_listings',
        'can_create_listing',
        'can_edit_own_listing',
        'can_delete_own_listing',
        'can_request_brand',
        'can_view_statistics',
    ],
    'manager': [
        'can_view_listings',
        'can_delete_any_listing',
        'can_deactivate_listing',
        'can_ban_user',
        'can_unban_user',
        'can_view_users',
        'can_review_brand_requests',
    ],
    'admin': [codename for codename, _, _ in PERMISSIONS],
}

ADMIN_USER = {
    'email': os.environ.get('ADMIN_EMAIL', 'admin@autoria.ua'),
    'password': os.environ.get('ADMIN_PASSWORD', 'Admin123!'),
    'first_name': 'Admin',
    'last_name': 'AutoRia',
}


class Command(BaseCommand):
    help = 'Seed roles, permissions, and admin user (idempotent via get_or_create)'

    def handle(self, *args, **options):
        self.stdout.write('Seeding permissions...')
        perm_objects = {}
        for codename, name, description in PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={'name': name, 'description': description},
            )
            perm_objects[codename] = perm
            if created:
                self.stdout.write(f'  Created permission: {codename}')

        self.stdout.write('Seeding roles...')
        for role_name, perm_codenames in ROLES.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                scope='platform',
                defaults={'description': f'{role_name.capitalize()} role'},
            )
            role.permissions.set([perm_objects[c] for c in perm_codenames])
            if created:
                self.stdout.write(f'  Created role: {role_name}')

        self.stdout.write('Seeding admin user...')
        admin_role = Role.objects.get(name='admin', scope='platform')
        user, created = User.objects.get_or_create(
            email=ADMIN_USER['email'],
            defaults={
                'first_name': ADMIN_USER['first_name'],
                'last_name': ADMIN_USER['last_name'],
                'role': admin_role,
                'is_staff': True,
            },
        )
        if created:
            user.set_password(ADMIN_USER['password'])
            user.save()
            self.stdout.write(f'  Created admin user: {ADMIN_USER["email"]}')

        # Seed regions
        self.stdout.write('Seeding regions...')
        from apps.listings.models import Region
        for region_name in REGIONS:
            _, created = Region.objects.get_or_create(name=region_name)
            if created:
                self.stdout.write(f'  Created region: {region_name}')

        # Seed car brands and models
        self.stdout.write('Seeding car brands and models...')
        from apps.cars.models import CarBrand, CarModel
        for brand_name, models in CAR_BRANDS_MODELS.items():
            brand, created = CarBrand.objects.get_or_create(name=brand_name)
            if created:
                self.stdout.write(f'  Created brand: {brand_name}')
            for model_name in models:
                _, created = CarModel.objects.get_or_create(
                    brand=brand,
                    name=model_name,
                )
                if created:
                    self.stdout.write(f'    Created model: {model_name}')

        # Fetch initial currency rates from PrivatBank
        self.stdout.write('Fetching initial currency rates...')
        try:
            from apps.currency.services import fetch_privatbank_rates
            fetch_privatbank_rates()
            self.stdout.write('  Fetched initial currency rates')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not fetch rates: {e}'))

        # Create Celery Beat periodic task for daily currency rate updates
        self.stdout.write('Setting up periodic tasks...')
        try:
            from django_celery_beat.models import IntervalSchedule, PeriodicTask
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=24,
                period=IntervalSchedule.HOURS,
            )
            _, created = PeriodicTask.objects.get_or_create(
                name='Fetch currency rates daily',
                defaults={
                    'task': 'apps.currency.tasks.fetch_currency_rates',
                    'interval': schedule,
                },
            )
            if created:
                self.stdout.write('  Created periodic task: fetch_currency_rates (every 24h)')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Could not create periodic task: {e}'))

        self.stdout.write(self.style.SUCCESS('Seed data complete.'))
