import uuid

from braces.views import CsrfExemptMixin
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import MultipleObjectsReturned
from django.http import HttpResponse
from django.utils import timezone
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.views.mixins import OAuthLibMixin
from rest_framework import permissions, mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import list_route, api_view, parser_classes, detail_route
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from Rides.filters import OwnerFilterBackend
from Rides.models import Route, Profile, Car, Marker, UserInRoute, Travel, Rate
from Rides.serializer import RouteSerializer, CarSerializer, ProfileSerializer, RateSerializer
from Rides.utils import udeg_valida


class RouteViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.DestroyModelMixin,
                   GenericViewSet):
    parser_classes = (JSONParser,)
    permission_classes = (IsAuthenticated,)
    queryset = Route.objects.all()
    filter_backends = ()

    def create(self, request, *args,**kwargs):
        route_serializer = RouteSerializer(data=request.data, context={'user': request.user})
        if route_serializer.is_valid(raise_exception=settings.DEBUG):
            route_serializer.save()
            return Response(route_serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Wrong data'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        route = self.get_object()
        if not route.is_active:
            route.car = None
            route.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'Route cannot be deleted when is active.'}, status=status.HTTP_409_CONFLICT)

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
            timezone.activate('America/Mexico_City')
            now = timezone.localtime(timezone.now())
            if (23, 59) > (now.hour, now.minute) > (5, 0):
                route = Route.objects.get(pk=pk, car__owner=request.user.profile)
                if not route.is_active:
                    if len(Route.objects.filter(is_active=True, car__owner=request.user.profile)) == 0:
                        Travel.objects.create(route=route, profile=request.user.profile)
                        route.is_active = True
                        route.chat_room = str(uuid.uuid4())
                        route.save()
                        return Response({
                            'ok': 'Route activated successfully.',
                            'chat_room': route.chat_room,
                        })
                    return Response({'error': 'You have another route active.'}, status=status.HTTP_409_CONFLICT)
                return Response({'ok': 'Route is active already.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'System only works from 5:00 AM to 11:59 PM'})
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist'}, status=status.HTTP_404_NOT_FOUND)

    @detail_route(['GET'])
    def finalize(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, car__owner=request.user.profile)
            if route.is_active:
                travel = Travel.objects.filter(route=route, profile=request.user.profile).order_by('-began').first()
                travel.ended = timezone.now()
                travel.save()
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
            UserInRoute.objects.get(profile=request.user.profile)
            return Response({'error': 'You are already in a route'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
        except UserInRoute.DoesNotExist:
            pass
        try:
            Route.objects.get(car__owner=request.user.profile, is_active=True)
            return Response({'error': 'You can not join to a route when you are in a active route already.'},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
        except Route.DoesNotExist:
            pass
        try:
            marker_pk = request.GET.get('marker_id', None)
            route = Route.objects.get(pk=pk, is_active=True, car__owner__type=request.user.profile.type)
            if route.car.owner == request.user.profile:
                return Response({'error': 'You can not join to your route.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            if route.available_seats != 0 and marker_pk is not None:
                marker = route.markers.get(pk=marker_pk)
                route.people_in_route.create(profile=request.user.profile, marker=marker)
                return Response({
                    'ok': 'Route assignation successfully.',
                    'profile': ProfileSerializer(instance=route.car.owner).data,
                    'car': CarSerializer(instance=route.car).data,
                    'chat_room': route.chat_room,
                }, status=status.HTTP_200_OK)
            return Response({'error': 'Route is full.'}, status=status.HTTP_409_CONFLICT)
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        except Marker.DoesNotExist:
            return Response({'error': 'Marker id does not exist in this route.'}, status=status.HTTP_404_NOT_FOUND)

    @detail_route(['GET'])
    def unjoin(self, request, pk=None):
        try:
            route = Route.objects.get(pk=pk, is_active=True, car__owner__type=request.user.profile.type)
            user_in_route = route.people_in_route.get(profile=request.user.profile)
            user_in_route.delete()
            return Response({'ok': 'Removed from route successfully'})
        except Route.DoesNotExist:
            return Response({'error': 'Route does not exists'}, status=status.HTTP_404_NOT_FOUND)
        except UserInRoute.DoesNotExist:
            return Response({'error': 'You are not joined in the route.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @list_route(['GET'])
    def has_active(self, request):
        try:
            return Response(
                RouteSerializer(Route.objects.get(is_active=True, car__owner=request.user.profile)).data
            )
        except Route.DoesNotExist:
            return Response({'error': 'User does not have an active route'}, status=status.HTTP_404_NOT_FOUND)

    @list_route(['GET'])
    def in_route(self, request):
        try:
            return Response(
                RouteSerializer(instance=UserInRoute.objects.get(profile=request.user.profile).route).data
            )
        except UserInRoute.DoesNotExist:
            return Response({'error': 'User does not have an active route'}, status=status.HTTP_404_NOT_FOUND)
        except MultipleObjectsReturned:
            return Response({'info': 'You were in a multiple routes and have been removed from all'})

    @list_route(['GET'])
    def ready(self, request):
        try:
            user_in_route = UserInRoute.objects.get(profile=request.user.profile)
            user_in_route.ready = True
            user_in_route.save()
            return Response({'ok': 'User ready'})
        except UserInRoute.DoesNotExist:
            return Response({'error': 'User does not have an active route'}, status=status.HTTP_404_NOT_FOUND)
        except MultipleObjectsReturned:
            return Response({'info': 'You were in a multiple routes and have been removed from all'})

    @detail_route(['POST'])
    def rate(self, request, *args, **kwargs):
        route = self.get_object()
        travel = Travel.objects.filter(route=route).order_by('-began').first()
        try:
            Rate.objects.get(travel=travel, from_profile=self.request.user.profile, to_profile=travel.profile)
            return Response(status=status.HTTP_404_NOT_FOUND)
        except Rate.DoesNotExist:
            pass
        rate_serializer = RateSerializer(data=request.data)
        rate_serializer.is_valid(raise_exception=True)
        rate_serializer.save(travel=travel, from_profile=self.request.user.profile, to_profile=travel.profile)
        return Response(rate_serializer.data, status=status.HTTP_201_CREATED)


class CarViewSet(mixins.CreateModelMixin,
                 mixins.UpdateModelMixin,
                 mixins.DestroyModelMixin,
                 mixins.ListModelMixin,
                 mixins.RetrieveModelMixin,
                 GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = CarSerializer
    queryset = Car.objects.all()
    filter_backends = (OwnerFilterBackend,)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user.profile)

    def retrieve(self, request, *args, **kwargs):
        self.filter_backends = ()
        return super().retrieve(request, *args, **kwargs)


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
        data = r.split(',')
        if data[0] != 'A':
            return Response({'error': 'Inactive user'})
        try:
            user = User.objects.get(username=username)
            user.set_password(nip)
            user.save()
        except User.DoesNotExist:
            user = User.objects.create(username=username)
            user.set_password(nip)
            user.save()
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
