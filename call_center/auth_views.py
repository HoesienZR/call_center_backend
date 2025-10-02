from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .models import CustomUser as User
from .models import OTP
from .serializers import CustomUserSerializer
import random
import requests
from django.conf import settings



class CustomAuthToken(ObtainAuthToken):
    """
    کلاس سفارشی برای دریافت توکن احراز هویت
    """

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'full_name': user.get_full_name(),
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    ورود کاربر و دریافت توکن
    """
    phone = request.data.get('phone')
    password = request.data.get('password')
    if phone is None or password is None:
        return Response({
            'error': 'شماره تماس و رمز عبور الزامی است'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Try to find user by email
    try:
        user_obj = User.objects.get(phone_number=phone)
        user = authenticate(username=user_obj.username, password=password)
    except User.DoesNotExist:
        user = None

    if not user:
        print('errorایمیل یا رمز عبور اشتباه است')
        return Response({
            'error': 'شماره تلفن  یا رمز عبور اشتباه است'
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        return Response({
            'error': 'حساب کاربری غیرفعال است'
        }, status=status.HTTP_401_UNAUTHORIZED)

    token, created = Token.objects.get_or_create(user=user)

    return Response({
        'token': token.key,
        'user_id': user.pk,
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'full_name': user.get_full_name(),
        "phone": phone,
    })


@api_view(['POST'])
def logout(request):
    """
    خروج کاربر و حذف توکن
    """
    try:
        request.user.auth_token.delete()
        return Response({
            'message': 'با موفقیت خارج شدید'
        }, status=status.HTTP_200_OK)
    except (AttributeError, Token.DoesNotExist):
        return Response({
            'error': 'توکن معتبری یافت نشد'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def user_profile(request):
    """
    دریافت اطلاعات پروفایل کاربر
    """
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    ثبت نام کاربر جدید با ایجاد پروفایل و شماره تلفن
    """

    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    phone_number = request.data.get('phone_number', '')  # دریافت شماره تلفن

    if not username or not password:
        return Response({
            'error': 'نام کاربری و رمز عبور الزامی است'
        }, status=status.HTTP_400_BAD_REQUEST)

    # بررسی اجباری بودن شماره تلفن
    if not phone_number:
        return Response({
            'error': 'شماره تلفن الزامی است'
        }, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({
            'error': 'نام کاربری قبلاً استفاده شده است'
        }, status=status.HTTP_400_BAD_REQUEST)

    # بررسی تکراری نبودن شماره تلفن (اختیاری)
    if User.objects.filter(phone_number=phone_number).exists():
        return Response({
            'error': 'شماره تلفن قبلاً استفاده شده است'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # ایجاد کاربر

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number

        )
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'کاربر با موفقیت ایجاد شد',
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        # در صورت بروز خطا، کاربر ایجاد شده را حذف کنیم
        if 'user' in locals():
            user.delete()

        return Response({
            'error': f'خطا در ایجاد کاربر: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def request_otp(request):
    phone = request.data.get('phone')
    if not phone:
        return Response({"error": "شماره تلفن الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    # بررسی وجود کاربر
    if not User.objects.filter(phone_number=phone).exists():
        return Response({"error": "کاربری با این شماره یافت نشد"}, status=status.HTTP_404_NOT_FOUND)

    otp_code = str(random.randint(100000, 999999))  # تولید OTP 6 رقمی

    # ذخیره OTP در دیتابیس
    OTP.objects.create(phone_number=phone, otp_code=otp_code)

    # ارسال OTP از طریق API پیامک TSMS
    username = settings.TSMS_USERNAME
    password = settings.TSMS_PASSWORD
    from_number = settings.TSMS_FROM_NUMBER

    message = f"کد تایید شما: {otp_code}"

    send_sms_url = (
        f"http://tsms.ir/url/tsmshttp.php?"
        f"from={from_number}&to={phone}&username={username}&password={password}&message={message}"
    )

    try:
        resp = requests.get(send_sms_url)
        if resp.status_code == 200:
            return Response({"message": "کد OTP ارسال شد"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "خطا در ارسال پیامک"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    phone = request.data.get('phone')
    otp_code = request.data.get('otp')

    if not phone or not otp_code:
        return Response({"error": "شماره تلفن و OTP الزامی است"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        otp_obj = OTP.objects.filter(phone_number=phone, otp_code=otp_code, is_verified=False).last()
        if not otp_obj or otp_obj.is_expired():
            return Response({"error": "OTP نامعتبر یا منقضی شده"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(phone_number=phone)
        otp_obj.is_verified = True
        otp_obj.save()

        token, created = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user_id": user.pk,
            "username": user.username,
            "phone": user.phone_number
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({"error": "کاربر یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
