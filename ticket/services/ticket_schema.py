from drf_spectacular.utils import extend_schema, extend_schema_view
from ticket.models import Ticket
from ticket.serializers import TicketSerializer

ticket_all_schema = extend_schema_view(
    list=extend_schema(
        summary="لیست تیکت‌ها",
        description="برگرداندن لیست تیکت‌های کاربر (یا همه تیکت‌ها بسته به لاجیک شما).",
        tags=["Tickets"],
        responses={200: TicketSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="جزییات یک تیکت",
        description="گرفتن جزییات یک تیکت بر اساس شناسه.",
        tags=["Tickets"],
        responses={200: TicketSerializer},
    ),
    create=extend_schema(
        summary="ایجاد تیکت جدید",
        description="ساخت تیکت جدید. فیلد user به صورت خودکار از روی کاربر لاگین‌ شده ست می‌شود.",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={201: TicketSerializer},
    ),
    update=extend_schema(
        summary="ویرایش کامل تیکت",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={200: TicketSerializer},
    ),
    partial_update=extend_schema(
        summary="ویرایش بخشی از تیکت",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={200: TicketSerializer},
    ),
    destroy=extend_schema(
        summary="حذف تیکت",
        tags=["Tickets"],
        responses={204: None},
    ),
)