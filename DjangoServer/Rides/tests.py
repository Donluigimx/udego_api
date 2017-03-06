import json

import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from oauth2_provider.models import Application, AccessToken
from requests.auth import HTTPBasicAuth
from rest_framework import status
from rest_framework.test import APITestCase

from Rides.models import Route, Profile, Car, Marker


class UserTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create(username='209528202')
        self.user.set_password('1234')
        self.user.save()
        self.profile = Profile.objects.create(name='Pedro', phone_number='3311995533', email='luis@gmail.com',
                                              code='209528202', type='A', university='CUCEI', user=self.user)
        self.car = Car.objects.create(owner=self.profile, model='Sentra 2014', color='Rojo Oscuro', license_plate='ALD-F2SA-2')
        application = Application(
            name="Test Application",
            redirect_uris="http://localhost",
            user=self.user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )
        application.save()
        self.access_token = AccessToken.objects.create(
            user=self.user, token='1234567890',
            application=application, scope='read write',
            expires=timezone.now() + datetime.timedelta(days=1)
        )

    def _create_authorization_header(self, token=None):
        return "Bearer {0}".format(token or self.access_token.token)

    def test_route(self):
        data = {
            'car_id': self.car.id,
            'destination': 'CUCEI',
            'markers': [
                {
                    'lat': 100.000001,
                    'lng': 100.000002
                },
                {
                    'lat': 100.000003,
                    'lng': 100.000004
                },
                {
                    'lat': 100.000005,
                    'lng': 100.000006
                }
            ]
        }
        auth = self._create_authorization_header()
        response = self.client.post('/api/routes/', data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route = Route.objects.get(id=1)
        route.is_active = True
        route.save()

        response = self.client.get('/api/routes/filter/?destination=CUCEI', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        route.is_active = False
        route.save()
        response = self.client.get('/api/routes/filter/?destination=CUCEI', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.data, [])

        response = self.client.get('/api/routes/filter/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get('/api/routes/{0}/active/'.format(route.id), HTTP_AUTHORIZATION=auth)
        route = Route.objects.get(pk=route.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(route.is_active, True)
        self.assertNotEqual(route.chat_room, None)

        response = self.client.delete('/api/routes/{0}/'.format(route.id), HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        response = self.client.get('/api/routes/{0}/finish/'.format(route.id), HTTP_AUTHORIZATION=auth)
        route = Route.objects.get(pk=route.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(route.chat_room, None)

        user = User.objects.create(username='Pee')
        profile = Profile.objects.create(name='Pedroo', phone_number='3311995533', email='lois@gmail.com',
                                         code='209528201', type='A', university='CUCEI',
                                         user=user
                                         )

        self.client.get('/api/routes/{0}/active/'.format(route.id), HTTP_AUTHORIZATION=auth)
        self.access_token.user = user
        self.access_token.save()

        response = self.client.get('/api/routes/{0}/assign/'.format(route.id), HTTP_AUTHORIZATION=auth)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(3, route.available_seats)
        self.assertEqual(route.people_in_route.first(), profile)

    def test_car(self):
        data = {
            'model': 'Sentra 2014',
            'color': 'Rojo fuerte',
            'license_plate': 'APD-212',
        }
        auth = self._create_authorization_header()
        response = self.client.post('/api/cars/', data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.user.id)

        response = self.client.delete('/api/cars/{0}/'.format(response.data['id']), HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(Car.objects.filter(owner=self.profile)), 1)


class UdeGTestCase(APITestCase):

    def setUp(self):
        application = Application(
            name="Test Application",
            redirect_uris="http://localhost",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        )
        application.save()
        self.access_token = AccessToken.objects.create(
            token='1234567890',
            application=application, scope='read write',
            expires=timezone.now() + datetime.timedelta(days=1)
        )

    def _create_authorization_header(self, token=None):
        return "Bearer {0}".format(token or self.access_token.token)

    def test_login(self):
        data = {
            'code': '209528202',
            'nip': 'holapito',
            'email': 'luigi.lahi@gmail.com',
            'phone_number': '3311995533',
            'password': '1122334455'
        }
        auth = self._create_authorization_header()

        response = self.client.post('/api/profile/udg_signup/', data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        first_response = response.data
        profile = Profile.objects.get(code='209528202')
        self.assertEqual(profile.type, 'A')
        user = User.objects.get(pk=response.data['id'])

        data = {
            'code': '208528202',
            'nip': 'pablito',
            'email': 'luigi.lahi@gmail.com',
            'phone_number': '3311995533',
            'password': '1122334455'
        }
        response = self.client.post('/api/profile/udg_signup/', data, format='json', HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        #
        #  Login created user
        #
        application = Application(
            name="Test Application",
            redirect_uris="http://localhost",
            user=user,
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )
        application.save()
        self.access_token = AccessToken.objects.create(
            user=user, token='1234567891',
            application=application, scope='read write',
            expires=timezone.now() + datetime.timedelta(days=1)
        )
        auth = self._create_authorization_header()
        response = self.client.get('/api/profile/', HTTP_AUTHORIZATION=auth)
        self.assertEqual(first_response, response.data)
