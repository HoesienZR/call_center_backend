from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import CustomUser as User
from .serializers import CustomUserSerializer
from .services import auth_schema
from .services import otp_service
from .services.auth_schema import auth_token_post_schema


class CustomAuthToken(ObtainAuthToken):
    """
    Custom class to obtain authentication token.
    """
    @auth_token_post_schema
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'full_name': user.get_full_name(),
        })


@auth_schema.login_post_schema
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    User login and obtain authentication token.
    """
    phone = request.data.get('phone')
    password = request.data.get('password')
    if phone is None or password is None:
        return Response({
            'error': 'Phone number and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Try to find user by phone number
    try:
        user_obj = User.objects.get(phone_number=phone)
        user = authenticate(phone_number=user_obj.phone_number, password=password)
    except User.DoesNotExist:
        user = None

    if not user:
        return Response({
            'error': 'Phone number or password is incorrect'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({
            'error': 'User account is inactive'
        }, status=status.HTTP_401_UNAUTHORIZED)

    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.pk,
        'email': user.email,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'full_name': user.get_full_name(),
        "phone": phone,
    })


@auth_schema.logout_post_schema
@api_view(['POST'])
def logout(request):
    """
    User logout and token deletion.
    """
    try:
        request.user.auth_token.delete()
        return Response({
            'message': 'Successfully logged out'
        }, status=status.HTTP_200_OK)
    except (AttributeError, Token.DoesNotExist):
        return Response({
            'error': 'Valid token not found'
        }, status=status.HTTP_400_BAD_REQUEST)


@auth_schema.user_profile_get_schema
@api_view(['GET'])
def user_profile(request):
    """
    Retrieve the profile information of the logged-in user.
    """
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


@auth_schema.register_post_schema
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user with profile and phone number.
    """
    password = request.data.get('password')
    email = request.data.get('email', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    phone_number = request.data.get('phone_number', '')

    if not password:
        return Response({
            'error': 'password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not phone_number:
        return Response({
            'error': 'Phone number is required'
        }, status=status.HTTP_400_BAD_REQUEST)


    if User.objects.filter(phone_number=phone_number).exists():
        return Response({
            'error': 'Phone number is already in use'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.create_user(
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'User successfully created',
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        if 'user' in locals():
            user.delete()
        return Response({
            'error': f'Error creating user: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@auth_schema.request_otp_post_schema
@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    phone = request.data.get('phone')

    if not phone:
        return Response({"error": "Phone number is required"}, status=400)

    user, _ = User.objects.get_or_create(
        phone_number=phone,
        password=phone

    )

    if not otp_service.can_request_otp(request, phone):
        return Response({"error": "Previous code still valid. Try later."}, status=429)

    otp_code = otp_service.generate_otp()
    otp_service.store_otp(request, phone, otp_code)

    otp_service.send_sms(phone, otp_code)

    return Response({"message": "OTP sent"}, status=200)


@auth_schema.verify_otp_post_schema
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp_code = request.data.get('otp')

    if not phone or not otp_code:
        return Response({"error": "Phone number and OTP are required"}, status=400)

    cached_otp = otp_service.get_cached_otp(request, phone)

    if not cached_otp or cached_otp != otp_code:
        return Response({"error": "Invalid or expired OTP"}, status=400)

    try:
        user = User.objects.get(phone_number=phone)
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    otp_service.clear_otp(request, phone)

    token, _ = Token.objects.get_or_create(user=user)

    return Response({
        "token": token.key,
        "user_id": user.pk,
        "phone": user.phone_number,
    }, status=200)
