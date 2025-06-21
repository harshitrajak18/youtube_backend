from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import random
import logging
from .models import EmailOTP, User
from .utils import send_email_to_client
from .serializer import CreateUserSerializer
from rest_framework.permissions import IsAuthenticated,AllowAny
from .serializer import *
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from django.shortcuts import get_object_or_404
logger = logging.getLogger(__name__)

# Create your views here.
class EmailRequest(APIView):
    
    def post(self, request):
        email = request.data.get('email')
        try:
            if not email:
                return Response({'message': "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
            user=User.objects.filter(email=email)
            if user.exists():
                return Response({'message':'Email is already taken'},status=status.HTTP_226_IM_USED)

            otp = str(random.randint(100000, 999999))
            EmailOTP.objects.update_or_create(email=email, defaults={'otp': otp})
            send_email_to_client(email, otp)

            return Response({'message': f'Email sent to the client {email}'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")


class RegisterUser(APIView):
    parser_classes = [JSONParser,MultiPartParser, FormParser]
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')

        if not email or not otp:
            return Response({'message': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            otp_record = EmailOTP.objects.filter(email=email).first()
            print(otp_record.otp)

            if not otp_record or otp_record.otp != otp:
                return Response({'message': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

            serializer = CreateUserSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                otp_record.delete()

                return Response({'message': 'User successfully registered'}, status=status.HTTP_201_CREATED)

            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return Response(
                {'message': 'Something went wrong. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class LoginUser(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not User.objects.filter(email=email).exists():
            return Response(
                {'message': 'Email does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {'message': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login Successful'
        })
        

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)

        profile_photo_url = request.build_absolute_uri(user.profile_image.url) if user.profile_image else None

        user_data = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile_photo': profile_photo_url,
        }

        videos = Video.objects.filter(uploaded_by=user)
        video_data = [
            {
                'title': video.title,
                'description': video.description,
                'video_url': video.video_file.url if video.video_file else None,
                'uploaded_at': video.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for video in videos
        ]

        return Response({
            'user': user_data,
            'videos': video_data
        })

class UploadVideoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, email):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Pass request.data directly, it includes both form fields and files
        serializer = VideoSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(uploaded_by=user)  # Use the actual user instance
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoFeedView(APIView):
    def get(self, request, *args, **kwargs):
        videos = Video.objects.all().order_by('-uploaded_at')[:50]
        videos_data = []
        for video in videos:
            videos_data.append({
                'id': video.id,
                'title': video.title,
                'description': (video.description[:150] + '...') if len(video.description) > 150 else video.description,
                'thumbnail_url': video.thumbnail.url if video.thumbnail else '',
                'video_url': video.video_file.url if video.video_file else '',
                'uploaded_at': video.uploaded_at.isoformat(),
                #'views': video.views,
                #'duration': video.duration,
                'uploaded_by': {
                    'username': video.uploaded_by.username,
                    'profile_photo': video.uploaded_by.profile.profile_image.url if hasattr(video.uploaded_by, 'profile') and video.uploaded_by.profile.profile_image else '',
                },
            })

        return Response({'videos': videos_data})  
    
class VideoDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        video = get_object_or_404(Video, id=id)
        user = request.user if request.user.is_authenticated else None

        liked = False
        if user:
            liked = Like.objects.filter(video=video, author=user).exists()

        data = {
            "id": video.id,
            "title": video.title,
            "video_url": str(video.video_file.url),
            "thumbnail_url": str(video.thumbnail.url) if video.thumbnail else "",
            "uploaded_by": {
                "username": video.uploaded_by.username,
                "profile_photo": str(video.uploaded_by.profile_image.url) if video.uploaded_by.profile_image else ""
            },
            "uploaded_at": video.uploaded_at.isoformat(),
            "description": video.description if hasattr(video, 'description') else "",
            "likes": video.likes.count(),
            "liked": liked,
        }
        return Response(data, status=status.HTTP_200_OK)


class LikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        video = get_object_or_404(Video, id=id)
        user = request.user

        like_obj, created = Like.objects.get_or_create(video=video, author=user)

        if not created:
            # Already liked, so unlike
            like_obj.delete()
            liked = False
        else:
            liked = True

        return Response({
            "liked": liked,
            "likes": video.likes.count()
        }, status=status.HTTP_200_OK)
    

class CommentView(APIView):

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []  # AllowAny (default) for GET

    def get(self, request, id):
        video = get_object_or_404(Video, id=id)
        comments = Comment.objects.filter(video=video).select_related("author").order_by('-created_at')

        comment_data = [
            {
                "user": comment.author.username,
                "text": comment.text,
                "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for comment in comments
        ]
        return Response({"comments": comment_data})

    def post(self, request, id):
        video = get_object_or_404(Video, id=id)
        text = request.data.get("text", "").strip()

        if not text:
            return Response({"error": "Comment text is required."}, status=400)

        comment = Comment.objects.create(
            video=video,
            author=request.user,
            text=text
        )

        return Response({
            "message": "Comment added successfully.",
            "comment": {
                "user": comment.author.username,
                "text": comment.text,
                "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        })