from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from contacts.serializers import ContactSerializer, ContactStatsSerializer

filter_contact_by_status_and_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="فیلتر مخاطبین بر اساس وضعیت و پروژه",
    description=(
        "لیستی از مخاطبین که بر اساس `status` و `project_id` فیلتر شده‌اند را برمی‌گرداند. "
        "این لیست شامل اطلاعات تماس‌گیرنده تخصیص داده‌شده، پروژه مربوطه و یادداشت‌های مرتبط با هر مخاطب می‌باشد."
    ),
    parameters=[
        OpenApiParameter(
            name='status',
            description='فیلتر مخاطبین بر اساس وضعیت تماس آنها',
            required=True,
            type=OpenApiTypes.STR
        ),
        OpenApiParameter(
            name='project_id',
            description='فیلتر مخاطبین بر اساس پروژه خاص',
            required=True,
            type=OpenApiTypes.INT
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="لیستی از مخاطبین فیلتر شده بر اساس وضعیت و پروژه."
        ),
        400: OpenApiResponse(description="پارامترهای جستجو ناقص یا نامعتبر هستند.")
    }
)

filter_contact_by_status_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="فیلتر مخاطبین بر اساس وضعیت",
    description="تمام مخاطبانی که با وضعیت داده‌شده مطابقت دارند را برمی‌گرداند.",
    parameters=[
        OpenApiParameter(
            name='status',
            description='وضعیت مخاطبین برای فیلتر کردن',
            required=True,
            type=OpenApiTypes.STR
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="لیست مخاطبین فیلتر شده."
        ),
        400: OpenApiResponse(description="پارامتر وضعیت مشخص نشده است.")
    }
)

filter_contact_by_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="فیلتر مخاطبین بر اساس پروژه",
    description="تمام مخاطبینی که به پروژه مشخص تعلق دارند را برمی‌گرداند.",
    parameters=[
        OpenApiParameter(
            name='project_id',
            description='شناسه پروژه برای فیلتر کردن',
            required=True,
            type=OpenApiTypes.INT
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="لیستی از مخاطبین متعلق به پروژه مشخص."
        ),
        400: OpenApiResponse(description="شناسه پروژه وارد نشده یا نامعتبر است.")
    }
)

get_contact_stats_schema = extend_schema(
    tags=['Contacts', 'Statistics'],
    summary="دریافت آمار مخاطب",
    description="آمار مربوط به هر مخاطب مانند تعداد تماس‌ها، تماس‌های پاسخ داده‌شده و ... را دریافت می‌کند.",
    responses={
        200: OpenApiResponse(
            response=ContactStatsSerializer,
            description="آمار دقیق از مخاطب."
        ),
        400: OpenApiResponse(description="داده‌های مخاطب نامعتبر است.")
    }
)

request_new_contact_schema = extend_schema(
    summary="درخواست یک مخاطب جدید برای پروژه",
    description=(
        "یک مخاطب آزاد از پروژه انتخاب‌شده را به کاربر احراز هویت شده تخصیص می‌دهد. "
        "کاربر باید مجوزهای تماس‌گیرنده، ادمین پروژه یا ادمین سیستم را داشته باشد."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "شناسه پروژه‌ای که مخاطب باید به آن تخصیص داده شود.",
                    "example": 42,
                }
            },
            "required": ["project_id"],
        }
    },
    responses={
        200: OpenApiResponse(
            description="مخاطب جدید با موفقیت به شما تخصیص داده شد.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "یک مخاطب جدید با موفقیت به شما تخصیص داده شد."}
                )
            ],
        ),
        400: OpenApiResponse(
            description="شناسه پروژه وارد نشده یا نامعتبر است.",
            examples=[
                OpenApiExample(
                    "Missing ID",
                    value={"detail": "شناسه پروژه مورد نیاز است."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="مخاطب آزاد یا پروژه پیدا نشد.",
            examples=[
                OpenApiExample(
                    "No Contacts",
                    value={"detail": "هیچ مخاطب آزاد برای تخصیص وجود ندارد."}
                )
            ],
        ),
    },
    parameters=[
        OpenApiParameter(
            name="Authorization",
            location=OpenApiParameter.HEADER,
            required=True,
            description="توکن دسترسی Bearer برای احراز هویت.",
            type=str,
        ),
    ],
)

release_contact_schema = extend_schema(
    tags=['Contacts', 'Release'],
    summary="آزاد کردن مخاطب",
    description=(
        "این عملیات برای آزاد کردن یک مخاطب تخصیص داده‌شده توسط تماس‌گیرنده یا ادمین است. "
        "مخاطب پس از آزاد شدن، به لیست عمومی مخاطبین بازمی‌گردد."
    ),
    parameters=[
        OpenApiParameter(
            name="contact_id",
            description="شناسه مخاطب که باید آزاد شود",
            required=True,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="مخاطب با موفقیت آزاد شد و به لیست عمومی بازگشت.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "مخاطب با موفقیت آزاد شد و به لیست عمومی بازگشت."}
                )
            ],
        ),
        403: OpenApiResponse(
            description="دسترسی غیرمجاز. کاربر اجازه آزاد کردن این مخاطب را ندارد.",
            examples=[
                OpenApiExample(
                    "Forbidden",
                    value={"detail": "شما اجازه آزاد کردن این مخاطب را ندارید."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="مخاطب یافت نشد.",
            examples=[
                OpenApiExample(
                    "Not Found",
                    value={"detail": "مخاطب مورد نظر یافت نشد."}
                )
            ],
        ),
    },
)
