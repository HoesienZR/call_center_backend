from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from contacts.models import Contact
from projects.models import Project
from .models import Call, CallEditHistory
from .serializers import CallSerializer, CallEditHistorySerializer
from .services.call_schema import call_schema, project_filter_schema, call_create_detail_schema, \
    call_edit_changesubmit_schema, caller_feedback_schema, detailed_report_schema, call_edit_history_schema


@call_schema
class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.select_related('contact', 'caller', 'project', 'edited_by').all()
    serializer_class = CallSerializer
    permission_classes = [IsAuthenticated]

    @project_filter_schema
    def get_queryset(self):
        project_id = self.request.GET.get('project_id')
        queryset = super().get_queryset()

        if self.request.user.is_staff:
            # admin همه کال‌ها را می‌تواند ببیند
            return queryset.filter(project_id=project_id) if project_id else queryset

        if project_id:
            project = get_object_or_404(Project, id=project_id)
            if project.created_by == self.request.user:
                return queryset.filter(project=project)
            return queryset.filter(caller=self.request.user, project=project)

        return queryset.filter(caller=self.request.user)

    def perform_create(self, serializer):
        serializer.save(caller=self.request.user)

    @call_create_detail_schema
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_call(self, request):
        contact_id = request.data.get('contact') or request.data.get('contact_id')
        project_id = request.data.get('project') or request.data.get('project_id')

        if not contact_id:
            return Response({"error": "contact_id الزامی است"}, status=400)

        contact = get_object_or_404(Contact, id=contact_id)
        project = get_object_or_404(Project, id=project_id) if project_id else None

        serializer_data = {
            "contact_id": contact.id,
            "caller_id": request.user.id,
            "project_id": project.id if project else None,
            "status": request.data.get('status', 'pending'),
            "call_result": request.data.get('call_result'),
            "notes": request.data.get('notes', ''),
            "duration": request.data.get('duration', 0),
            "follow_up_required": request.data.get('call_result') == 'callback_requested',
            "follow_up_date": request.data.get('follow_up_date'),
        }

        serializer = CallSerializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        serializer.save(caller=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @call_edit_changesubmit_schema
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def edit_call(self, request, pk=None):
        call = self.get_object()

        if not (call.caller == request.user or request.user.is_staff):
            return Response({"detail": "شما اجازه ویرایش ندارید."}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(call, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        call.save_original_data_if_first_edit()

        edits = []
        for attr, new_value in serializer.validated_data.items():
            old_value = getattr(call, attr)
            if old_value != new_value:
                edits.append(CallEditHistory(
                    call=call,
                    edited_by=request.user,
                    field_name=attr,
                    old_value=str(old_value),
                    new_value=str(new_value),
                    edit_reason=request.data.get("edit_reason", "")
                ))

        CallEditHistory.objects.bulk_create(edits)
        serializer.save(edited_by=request.user, edit_reason=request.data.get("edit_reason", ""),
                        edited_at=timezone.now())
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)

    @caller_feedback_schema
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_feedback(self, request, pk=None):
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما اجازه ثبت بازخورد ندارید."}, status=status.HTTP_403_FORBIDDEN)

        feedback = request.data.get("notes")
        call_status = request.data.get("status")
        if feedback:
            call.feedback = feedback
        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, status=400)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=status.HTTP_200_OK)

    @detailed_report_schema
    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_detailed_report(self, request, pk=None):
        call = self.get_object()
        if call.caller != request.user:
            return Response({"detail": "شما اجازه ثبت گزارش ندارید."}, status=403)

        report = request.data.get("report_data")
        call_status = request.data.get("call_status")
        if report:
            call.detailed_report = report
        if call_status:
            if call_status not in [choice[0] for choice in Call.CALL_STATUS_CHOICES]:
                return Response({"error": "وضعیت تماس نامعتبر است."}, 400)
            call.status = call_status

        call.save()
        return Response(self.get_serializer(call).data, status=200)


@call_edit_history_schema
class CallEditHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CallEditHistory.objects.all()
    serializer_class = CallEditHistorySerializer
    permission_classes = [IsAdminUser]
