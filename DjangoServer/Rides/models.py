from django.contrib.auth.models import User
from django.contrib.postgres import validators
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(User)
    name = models.CharField(max_length=64)
    phone_number = models.CharField(max_length=16, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    code = models.CharField(max_length=64, unique=True)
    type = models.CharField(max_length=1)
    university = models.CharField(max_length=64)
    photo = models.ImageField(upload_to='images/profile/', null=True, blank=True)
    rate = models.FloatField(
        default=5,
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(5)]
    )

    def __str__(self):
        return self.name


class Car(models.Model):
    owner = models.ForeignKey(Profile, related_name='cars')
    model = models.CharField(max_length=64)
    color = models.CharField(max_length=32)
    license_plate = models.CharField(max_length=32)

    def __str__(self):
        return "%s %s %s" % (self.model, self.color, self.license_plate)


class Route(models.Model):
    car = models.ForeignKey(Car, related_name='routes', null=True)
    destination = models.CharField(max_length=32)
    is_active = models.BooleanField(default=False)
    seats = models.IntegerField(default=4)
    chat_room = models.CharField(null=True, max_length=64)

    @property
    def available_seats(self):
        return self.seats - len(self.people_in_route.all())

    def __str__(self):
        return "%s %s" % (self.car, self.destination)


class Marker(models.Model):
    route = models.ForeignKey(Route, related_name='markers')
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    description = models.CharField(max_length=64)

    def __str__(self):
        return "%s %s" % (self.route, self.description)


class UserInRoute(models.Model):
    route = models.ForeignKey(Route, related_name='people_in_route')
    profile = models.ForeignKey(Profile)
    marker = models.ForeignKey(Marker)
    ready = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s %s" % (self.route, self.profile, self.marker)


class Travel(models.Model):

    route = models.ForeignKey('Rides.Route')
    profile = models.ForeignKey('Rides.Profile')
    began = models.DateTimeField(auto_now_add=True)
    ended = models.DateTimeField(null=True)

    def __str__(self):
        return "%s %s began:%s, ended:%s" % \
               (self.profile, self.route, self.began.isoformat(), self.ended.isoformat())


class Rate(models.Model):

    travel = models.ForeignKey('Rides.Travel')
    from_profile = models.ForeignKey('Rides.Profile', related_name='rates')
    to_profile = models.ForeignKey('Rides.Profile', related_name='rated')
    rate = models.IntegerField(
        validators=[validators.MinValueValidator(0), validators.MaxValueValidator(5)]
    )

    def __str__(self):
        return "%s rate %s with %d" % \
               (self.from_profile, self.to_profile, self.rate)
