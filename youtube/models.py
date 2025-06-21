from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from cloudinary.models import CloudinaryField

# Create your models here.
class User(AbstractUser):
    email = models.EmailField(unique=True)
    profile_image = CloudinaryField('image', blank=True, null=True)  

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class EmailOTP(models.Model):
    email = models.EmailField(unique=True, default='harshitrajak18@gmail.com')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return timezone.now() - self.created_at < timezone.timedelta(minutes=5)
    
class Video(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    video_file = CloudinaryField(resource_type='video')

    #
    thumbnail = CloudinaryField(resource_type='image')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    video= models.ForeignKey(Video , related_name='comments', on_delete=models.CASCADE)
    author= models.ForeignKey(User, on_delete=models.CASCADE)
    text= models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)

class Like(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')
    author= models.ForeignKey(User, on_delete=models.CASCADE)
    created_at=models.DateTimeField(auto_now_add=True)

