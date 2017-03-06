from django.conf.urls import url
from rest_framework import routers

from Rides import views

router = routers.SimpleRouter()
router.register(r'routes', views.RouteViewSet, 'Routes')
router.register(r'cars', views.CarViewSet, 'Cars')
router.register(r'profile', views.ProfileViewSet, 'Profiles')

urlpatterns = [
    url(r'^profile/udg_signup/$', views.udg_signup),
]

urlpatterns += router.urls
