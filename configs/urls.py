from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/roles/', include('apps.roles.urls')),
    path('api/cars/', include('apps.cars.urls')),
    path('api/listings/', include('apps.listings.urls')),
    path('api/currency/', include('apps.currency.urls')),
    path('api/statistics/', include('apps.statistics.urls')),
    path('api/dealerships/', include('apps.dealerships.urls')),
    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
