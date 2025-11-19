from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from .serializers import CallSerializer, CallEditHistorySerializer
from .models import Call, CallEditHistory, CallAnswer
from contacts.models import Contact
from projects.models import Project


# اسکیمای عمومی برای مدیریت تماس‌ها
call_schema = extend_schema(
    tags=["Calls"],
    description="مدیریت تماس‌ها شامل مشاهده، ایجاد، ویرایش و ثبت بازخورد"
)

# اسکیمای فیلتر بر اساس پروژه
project_filter_schema = extend_schema(
    parameters=[
        OpenApiParameter("project_id", str, description="فیلتر تماس‌ها بر اساس ID پروژه", required=False),
    ],
    description="نمایش لیست تماس‌ها بر اساس سطح دسترسی کاربر و شناسه پروژه (در صورت وجود)."
)

# اسکیمای ایجاد تماس جدید
call_create_detail_schema = extend_schema(
    description="ایجاد یک تماس جدید با جزئیات کامل تماس.",
    request=CallSerializer,
    responses={201: CallSerializer},
    examples=[
        OpenApiExample(
            "نمونه درخواست تماس جدید",
            value={
                "contact_id": 5,
                "project_id": 3,
                "status": "completed",
                "call_result": "successful",
                "notes": "تماس موفق انجام شد.",
                "duration": 120
            }
        )
    ]
)

# اسکیمای ویرایش تماس و ثبت تاریخچه تغییرات
call_edit_changesubmit_schema = extend_schema(
    description="ویرایش اطلاعات تماس با ثبت تاریخچه تغییرات.",
    request=CallSerializer,
    responses={200: CallSerializer},
    examples=[
        OpenApiExample(
            "نمونه ویرایش تماس",
            value={"notes": "به مشتری اطلاع داده شد.", "edit_reason": "به‌روزرسانی یادداشت‌ها"}
        )
    ]
)

# اسکیمای ثبت بازخورد تماس توسط تماس‌گیرنده
caller_feedback_schema = extend_schema(
    description="ثبت بازخورد تماس توسط تماس‌گیرنده.",
    request={
        "type": "object",
        "properties": {
            "notes": {
                "type": "string",
                "example": "مشتری پاسخ نداد.",
                "description": "یادداشت یا توضیحی درباره وضعیت تماس."
            },
            "status": {
                "type": "string",
                "example": "failed",
                "description": "وضعیت نهایی تماس (مثال: failed, completed)."
            }
        }
    },
    responses={200: CallSerializer}
)

# اسکیمای ثبت گزارش تفصیلی برای تماس
detailed_report_schema = extend_schema(
    description="ثبت گزارش تفصیلی برای تماس (مناسب برای گزارش‌های کامل تماس‌ها).",
    request={
        "type": "object",
        "properties": {
            "report_data": {
                "type": "object",
                "example": {"summary": "مذاکره درباره قرارداد جدید"}
            },
            "call_status": {
                "type": "string",
                "example": "completed"
            }
        }
    },
    responses={200: CallSerializer}
)

# اسکیمای GET لیست تاریخچه ویرایش تماس‌ها
list_call_edit_history_schema = extend_schema(
    summary="لیست تاریخچه ویرایش تماس‌ها",
    description="دریافت لیست تمام تاریخچه‌های ویرایش تماس‌ها. فقط کاربران admin دسترسی دارند.",
    responses={
        200: OpenApiResponse(
            response=CallEditHistorySerializer,
            description="لیست تاریخچه ویرایش تماس‌ها",
            examples=[
                OpenApiExample(
                    "نمونه پاسخ",
                    value=[{
                        "id": 1,
                        "call": 101,
                        "edited_by": 5,
                        "edit_date": "2025-11-14T12:00:00Z",
                        "field_name": "status",
                        "old_value": "pending",
                        "new_value": "completed",
                        "edit_reason": "تایید توسط سرپرست"
                    }]
                )
            ]
        ),
        403: OpenApiResponse(description="دسترسی غیرمجاز"),
    }
)

# اسکیمای GET جزئیات تاریخچه ویرایش تماس
retrieve_call_edit_history_schema = extend_schema(
    summary="جزئیات تاریخچه ویرایش تماس",
    description="دریافت یک رکورد مشخص از تاریخچه ویرایش تماس با ID.",
    responses={
        200: OpenApiResponse(
            response=CallEditHistorySerializer,
            description="جزئیات یک تاریخچه ویرایش تماس",
            examples=[
                OpenApiExample(
                    "نمونه پاسخ",
                    value={
                        "id": 1,
                        "call": 101,
                        "edited_by": 5,
                        "edit_date": "2025-11-14T12:00:00Z",
                        "field_name": "status",
                        "old_value": "pending",
                        "new_value": "completed",
                        "edit_reason": "تایید توسط سرپرست"
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="رکورد پیدا نشد"),
        403: OpenApiResponse(description="دسترسی غیرمجاز"),
    }
)
