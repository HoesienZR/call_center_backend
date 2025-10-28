from datetime import datetime

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from contacts.models import Contact
from projects.models import Project
from .serializers import *


class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.request.GET.get('project_id')
        if project_id:
            project = get_object_or_404(Project, id=project_id)
        queryset = super().get_queryset()
        if self.request.user.is_staff:
            return queryset
        if project_id and project.created_by == self.request.user:
            return queryset.filter(project=project)
        # Callers can only see their own calls
        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_call(self, request):
        """
        ایجاد یک تماس جدید با بازخورد
        """
        contact_id = request.data.get('callecaller_id') or request.data.get('contact_id')
        project_id = request.data.get('project_id')

        if not contact_id:
            return Response({"error": "contact_id الزامی است"}, status=400)

        try:
            contact = Contact.objects.get(id=contact_id)
            project = Project.objects.get(id=project_id) if project_id else None
        except (Contact.DoesNotExist, Project.DoesNotExist):
            return Response({"error": "Contact یا Project یافت نشد"}, status=404)

        serializer_data = {"contact": contact_id,
                           "caller_id": request.user.id,
                           "project": project_id,
                           "status": request.data.get('status', 'completed'),
                           "call_result": request.data.get('call_result'),
                           "notes": request.data.get('notes', ''),
                           "duration": request.data.get('duration', 0),
                           "follow_up_required": request.data.get('call_result') == 'callback_requested',
                           "follow_up_date": request.data.get('follow_up_date'),
                           }
        serializer_data.update({k: v for k, v in request.data.items() if k not in serializer_data})
        call_serializer = CallSerializer(data=serializer_data)
        if call_serializer.is_valid(raise_exception=True):
            call_serializer.save(caller_id=self.request.user.id)
            return Response(call_serializer.data, status=status.HTTP_201_CREATED)

        return Response(call_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def edit_call(self, request, pk=None):
        call = self.get_object()
        if not call.can_edit(request.user):
            return Response({"detail": "You are not authorized to edit this call."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(call, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Save original data if it\"s the first edit
        call.save_original_data_if_first_edit()

        # Manually save changes and create CallEditHistory
        for attr, value in serializer.validated_data.items():
            if hasattr(call, attr) and getattr(call, attr) != value:
                CallEditHistory.objects.create(
                    call=call,
                    edited_by=request.user,
                    field_name=attr,
                    old_value=str(getattr(call, attr)),
                    new_value=str(value),
                    edit_reason=request.data.get("edit_reason", "")
                )
                setattr(call, attr, value)

        call.edited_at = datetime.now()
        call.edited_by = request.user
        call.edit_reason = request.data.get("edit_reason", "")
        call.save()

        return Response(self.get_serializer(call).data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_feedback(self, request, pk=None):
        """
        ثبت بازخورد برای یک تماس موجود.
        """
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما مجاز به ثبت بازخورد برای این تماس نیستید."},
                            status=status.HTTP_403_FORBIDDEN)

        feedback_text = request.data.get("notes")
        call_status = request.data.get("status")
        if not feedback_text and not call_status:
            return Response({"error": "حداقل یکی از فیلدهای feedback_text یا call_status الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)

        if feedback_text:
            call.feedback = feedback_text

        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_detailed_report(self, request, pk=None):
        """
        ثبت گزارش تفصیلی برای یک تماس موجود.
        """
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما مجاز به ثبت گزارش برای این تماس نیستید."}, status=status.HTTP_403_FORBIDDEN)

        report_data = request.data.get("report_data")  # انتظار یک دیکشنری یا JSON برای گزارش تفصیلی
        call_status = request.data.get("call_status")

        if not report_data and not call_status:
            return Response({"error": "حداقل یکی از فیلدهای report_data یا call_status الزامی است."},
                            status=status.HTTP_400_BAD_REQUEST)

        if report_data:
            call.detailed_report = report_data

        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)


class CallEditHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallEditHistory.objects.all()
    serializer_class = CallEditHistorySerializer
    permission_classes = [IsAdminUser]
