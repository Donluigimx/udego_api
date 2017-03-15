from django.contrib.auth.models import User
from rest_framework import serializers

from Rides.models import Route, Marker, Car, Profile
from Rides.utils import udeg_valida, from_b64


class ProfileSerializer(serializers.ModelSerializer):

    nip = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)
    photo_data = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Profile
        fields = '__all__'
        read_only_fields = ('user', 'name', 'type', 'university', 'photo',)
        extra_kwargs = {
            'code': {
                'required': False,
            },
        }

    def validate(self, attrs):
        if 'new_user' in self.context:
            if not self.context['new_user']:
                raise serializers.ValidationError({'error': 'Luigi has autism.'})
            if not all(data in attrs for data in ('nip', 'password', 'code')):
                raise serializers.ValidationError({'error': 'Nip, password and code required to create user'})
            try:
                Profile.objects.get(code=attrs['code'])
                raise serializers.ValidationError({'error': 'User with code {0} already exists.'.format(attrs['code'])})
            except Profile.DoesNotExist:
                r = udeg_valida(**attrs)
                if r == '0':
                    raise serializers.ValidationError({'error': 'UdeG code or nip wrong'})
                data = r.split(',')
                attrs['name'] = data[2]
                attrs['type'] = data[0]
                attrs['university'] = data[3]

                return attrs

    def create(self, validated_data):
        profile = Profile(
            name=validated_data['name'],
            phone_number=validated_data['phone_number'],
            email=validated_data['email'],
            code=validated_data['code'],
            type=validated_data['type'],
            university=validated_data['university'],
        )
        if 'photo_data' in validated_data:
            content, name = from_b64(validated_data['photo_data'])
            profile.photo.save(name=name, content=content)
        user = User(username=validated_data['code'])
        user.set_password(raw_password=validated_data['password'])
        user.save()
        profile.user = user
        profile.save()

        return profile

    def update(self, instance, validated_data):
        instance.email = validated_data['email']
        instance.phone_number = validated_data['phone_number']
        if 'photo_data' in validated_data:
            content, name = from_b64(validated_data['photo_data'])
            instance.photo.save(name=name, content=content)

        return instance


class RouteSerializer(serializers.ModelSerializer):

    class MarkerSerializer(serializers.ModelSerializer):

        class Meta:
            model = Marker
            exclude = ('route', 'id')
            extra_kwargs = {
                'order': {
                    'read_only': True,
                }
            }

    markers = MarkerSerializer(required=True, many=True)
    car_id = serializers.SlugRelatedField(
        queryset=Car.objects.all(),
        slug_field='id',
        write_only=True,
        required=True,
    )

    people_in_route = ProfileSerializer(many=True, read_only=True)

    class Meta:
        model = Route
        fields = '__all__'
        depth = 1
        read_only = ('car', 'chat_room', 'people_in_route')

    def validate(self, attrs):
        if attrs['car_id'].owner != self.context['user'].profile:
            raise serializers.ValidationError({'error': 'You do not own this car.'})

    def create(self, validated_data):
        route = Route.objects.create(
            car=validated_data['car_id'],
            destination=validated_data['destination']
        )
        for marker in validated_data['markers']:
            Marker.objects.create(
                route=route,
                lat=marker['lat'],
                lng=marker['lng'],
            )
        return route


class CarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Car
        fields = '__all__'
        read_only_fields = ('owner',)

    def create(self, validated_data):
        if not 'owner' in self.context:
            raise serializers.ValidationError({'error': 'Profile user is mandatory'})
        validated_data['owner'] = self.context['owner']
        return Car.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.model = validated_data['model']
        instance.color = validated_data['color']
        instance.license_plate = validated_data['license_plate']
        return instance
