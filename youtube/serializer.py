from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import *

User = get_user_model()

class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'profile_image']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already in use")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
class VideoSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # Display email/username
    video_file = serializers.FileField()
    thumbnail = serializers.ImageField(required=False)

    class Meta:
        model = Video
        fields = ['id', 'user', 'title', 'description', 'video_file', 'thumbnail']


class LikeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # shows user email/username
    video = serializers.PrimaryKeyRelatedField(read_only=True)  # optional, can be writeable

    class Meta:
        model = Like
        fields = ['id', 'user', 'video', 'created_at']


       