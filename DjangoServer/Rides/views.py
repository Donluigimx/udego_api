import uuid

from braces.views import CsrfExemptMixin
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.views.mixins import OAuthLibMixin
from rest_framework import permissions
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import list_route, api_view, parser_classes, detail_route
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Rides.models import Route, Profile, Car
from Rides.serializer import RouteSerializer, CarSerializer, ProfileSerializer
from Rides.utils import udeg_valida


class RouteViewSet(viewsets.ViewSet):
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated, )

    def list(self, request):
        return Response(
            RouteSerializer(instance=Route.objects.filter(car__owner=request.user.profile), many=True)
        )

    def create(self, request):
        route_serializer = RouteSerializer(data=request.data)
        if route_serializer.is_valid(raise_exception=settings.DEBUG):
            route_serializer.save()
            return Response(route_serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Wrong data'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, car__owner=request.user.profile)
            if not route.is_active:
                route.delete()
                return Response({'ok', 'Route deleted successfully.'}, status=status.HTTP_200_OK)
            return Response({'error': 'Route cannot be deleted when is active.'}, status=status.HTTP_409_CONFLICT)
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist.'}, status=status.HTTP_404_NOT_FOUND)

    @list_route(['GET'])
    def filter(self, request):
        destination = self.request.query_params.get('destination', None)
        if destination is None:
            return Response({'error': 'Destination is a mandatory field.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            RouteSerializer(
                instance=[route for route in Route.objects.filter(is_active=True, destination=destination,
                                                                  car__owner__type=request.user.profile.type) if
                          route.available_seats > 0],
                many=True).data
        )

    @detail_route(['GET'])
    def activate(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, car__owner=request.user.profile)
            if not route.is_active:
                if len(Route.objects.filter(is_active=True, car__owner=request.user.profile)) == 0:
                    route.is_active = True
                    route.chat_room = str(uuid.uuid4())
                    route.save()
                    return Response({
                        'ok': 'Route activated successfully.',
                        'chat_room': route.chat_room,
                    })
                return Response({'error': 'You have another route active.'}, status=status.HTTP_409_CONFLICT)
            return Response({'ok': 'Route is active already.'}, status=status.HTTP_200_OK)
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist'}, status=status.HTTP_404_NOT_FOUND)

    @detail_route(['GET'])
    def finalize(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, car__owner=request.user.profile)
            if route.is_active:
                route.is_active = False
                route.chat_room = None
                [user.delete() for user in route.people_in_route.all()]
                route.save()
                return Response({'ok': 'Route finished successfully.'}, status=status.HTTP_200_OK)
            return Response({'error': 'Route is not active.'}, status=status.HTTP_409_CONFLICT)
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist'}, status=status.HTTP_404_NOT_FOUND)

    @detail_route(['GET'])
    def join(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, is_active=True, car__owner__type=request.user.profile.type)
            if route.available_seats != 0:
                route.people_in_route.add(request.user.profile)
                return Response({
                    'ok': 'Route assignation successfully.',
                    'profile': ProfileSerializer(instance=route.car.owner).data,
                    'car': CarSerializer(instance=route.car).data,
                    'chat_room': route.chat_room,
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Route is full.'}, status=status.HTTP_409_CONFLICT)
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist.'}, status=status.HTTP_404_NOT_FOUND)


class CarViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated,)

    def create(self, request):
        car_serializer = CarSerializer(data=request.data, context={'owner': request.user.profile})
        if car_serializer.is_valid(raise_exception=settings.DEBUG):
            car_serializer.save()
            return Response(car_serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Wrong data.'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            car_serializer = CarSerializer(data=request.data, instance=Car.objects.get(pk=pk, owner=request.user.profile))
        except Car.DoesNotExist:
            return Response({'error': 'Car does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        if car_serializer.is_valid():
            car_serializer.save()
            return Response(car_serializer.data)
        return Response({'error': 'Wrong data'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            car = Car.objects.get(pk=pk, owner=request.user.profile)
            if all([not route.is_active for route in car.routes.all()]):
                car.delete()
                return Response({'ok': 'Car deleted successfully.'}, status=status.HTTP_200_OK)
            return Response({'error': 'Car is an active route.'}, status=status.HTTP_409_CONFLICT)
        except Car.DoesNotExist:
            return Response({'error': 'Car does not exist'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@parser_classes((JSONParser,))
def udg_signup(request):
    profile_serializer = ProfileSerializer(data=request.data, context={'new_user': True})
    if profile_serializer.is_valid(raise_exception=settings.DEBUG):
        profile_serializer.save()
        return Response(profile_serializer.data, status=status.HTTP_201_CREATED)
    return Response({'error': 'Wrong data'}, status=status.HTTP_400_BAD_REQUEST)


class ProfileViewSet(viewsets.ViewSet):
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, pk=None):
        try:
            return Response(ProfileSerializer(
                instance=request.user.profile,
            ).data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, pk=None):
        profile_serializer = ProfileSerializer(data=request.data, instance=Profile.objects.get(pk=pk))
        if profile_serializer.is_valid(raise_exception=settings.DEBUG):
            profile_serializer.save()
            return Response(profile_serializer.data, status=status.HTTP_200_OK)
        return Response({'error': 'Wrong data.'}, status=status.HTTP_400_BAD_REQUEST)


class UdeGTokenView(APIView, CsrfExemptMixin, OAuthLibMixin):

    permission_classes = (permissions.AllowAny,)
    server_class = oauth2_settings.OAUTH2_SERVER_CLASS
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = oauth2_settings.OAUTH2_BACKEND_CLASS

    def post(self, request):
        username = request.POST.get('username')
        nip = request.POST.get('password')

        r = udeg_valida(code=username, nip=nip)
        if r == '0':
            return Response({'error': 'Wrong Username'})
        try:
            user = User.objects.get(username=username)
            user.set_password(nip)
            user.save()
        except User.DoesNotExist:
            user = User.objects.create(username=username)
            user.set_password(nip)
            user.save()
            print(r, r.split(','))
            data = r.split(',')
            Profile.objects.create(
                user=user,
                name=data[2],
                code=username,
                type=data[0],
                university=data[3],
            )
        url, headers, body, status = self.create_token_response(request)
        response = HttpResponse(content=body, status=status)

        for k, v in headers.items():
            response[k] = v
        return response
