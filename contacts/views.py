import logging
import traceback

from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.excel_imports import import_contacts_from_excel
from core.permissions import IsAdminOrProjectAdminOrProjectCaller, IsAdminOrProjectAdmin, ReleaseContactPermission
from projects.models import Project, ProjectMembership
from .models import Contact
from .schema import contact_schema, request_new_contact_schema, schema_contact_import
from .serializers import ContactSerializer, ContactStatsSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


@contact_schema
class ContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contacts with permissions-based queryset.
    Handles: listing, creating, updating, filtering, requesting new contacts,
    releasing contacts, submitting calls, and viewing contact stats.
    """
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsAdminOrProjectAdminOrProjectCaller]

    def get_serializer_context(self):
        return {'request': self.request, 'view': self, 'format': self.format_kwarg}

    def get_queryset(self):
        """
        Return contacts based on user permissions:
        - Superuser: all contacts
        - Project Admin: contacts in projects they admin
        - Caller: only contacts assigned to them
        """
        user = self.request.user
        if not user.is_authenticated:
            return Contact.objects.none()
        base_qs = Contact.objects.select_related('project', 'assigned_caller').prefetch_related('calls')

        if user.is_superuser:
            qs = base_qs
        else:
            # Projects where user is a member
            user_projects = Project.objects.filter(members=user)
            # Admin of any project
            if ProjectMembership.objects.filter(project__in=user_projects, user=user, role='admin').exists():
                qs = base_qs.filter(project__in=user_projects)
            else:
                # Only contacts assigned to the caller
                qs = base_qs.filter(assigned_caller=user)

        return qs.annotate(
            total_calls=Count('calls', distinct=True),
            answered_calls=Count('calls', filter=Q(calls__status='answered'), distinct=True),
            not_answered_calls=Count('calls', filter=Q(calls__status='no_answer'), distinct=True),
            interested_calls=Count('calls', filter=Q(calls__call_result='interested'), distinct=True),
            not_interested_calls=Count('calls', filter=Q(calls__call_result='not_interested'), distinct=True),
            no_time_calls=Count('calls', filter=Q(calls__call_result='no_time'), distinct=True),
        )

    def perform_create(self, serializer):
        """
        Assign caller automatically if user is a caller in the project.
        """
        user = self.request.user
        project = serializer.validated_data['project']

        if not serializer.validated_data.get('assigned_caller'):
            try:
                membership = ProjectMembership.objects.get(project=project, user=user)
                if membership.role == 'caller':
                    serializer.validated_data['assigned_caller'] = user
            except ProjectMembership.DoesNotExist:
                pass

        serializer.save(created_by=user)

    # ----------------- Actions -----------------
    @request_new_contact_schema
    @action(detail=False, methods=['post'], url_path='request_new')
    def request_new_contact(self, request):
        """
        Request a new contact for a caller.
        """
        project_id = request.data.get('project_id')
        if not project_id:
            return Response({"detail": "Project ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(Project, id=project_id)

        # Check if user is a member
        if not ProjectMembership.objects.filter(project=project, user=request.user).exists():
            return Response({"detail": "You are not a member of this project."}, status=status.HTTP_403_FORBIDDEN)

        # Find an available contact
        available_contact = Contact.objects.filter(
            project=project,
            assigned_caller__isnull=True,
            call_status='pending',
            is_active=True
        ).first()

        if not available_contact:
            return Response({"detail": "No available contacts to assign."}, status=status.HTTP_404_NOT_FOUND)

        available_contact.assigned_caller = request.user
        available_contact.save()

        return Response({"detail": "A new contact has been assigned to you."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='release', permission_classes=[ReleaseContactPermission])
    def release_contact(self, request, pk=None):
        """
        Release a contact back to the pool if assigned to the user.
        """
        contact = self.get_object()
        contact.assigned_caller = None
        contact.save()
        return Response({'detail': 'Contact successfully released.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='stats')
    def get_contact_stats(self, request, pk=None):
        """
        Return contact statistics.
        """
        contact = self.get_object()
        serializer = ContactStatsSerializer(contact, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # ----------------- Filtering -----------------
    @action(detail=False, methods=['get'], url_path='filter_by_status')
    def filter_by_status(self, request):
        status_val = request.GET.get('status')
        if not status_val:
            return Response({'detail': 'Status is required.'}, status=status.HTTP_400_BAD_REQUEST)

        contacts = self.get_queryset().filter(call_status=status_val)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='filter_by_project')
    def filter_by_project(self, request):
        project_id = request.GET.get('project_id')
        if not project_id:
            return Response({'detail': 'Project ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        contacts = self.get_queryset().filter(project_id=project_id)
        serializer = self.get_serializer(contacts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

@schema_contact_import
class ContactImportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrProjectAdmin]

    def post(self, request, project_id):
        """
        آپلود فایل اکسل و افزودن مخاطبین جدید.
        اگر تماس‌گیرنده وجود داشته باشد، اختصاص داده می‌شود.
        """
        project = get_object_or_404(Project, id=project_id)
        file_obj = request.FILES.get("file")

        if not file_obj:
            return Response(
                {"error": "فایل اکسل ارسال نشده است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            created_contacts = import_contacts_from_excel(file_obj, project)
            return Response(
                {
                    "message": f"{len(created_contacts)} مخاطب با موفقیت اضافه شد.",
                    "created_count": len(created_contacts),
                    "contacts": created_contacts,
                    "project": project.name,
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            traceback.print_exc()
            return Response(
                {"error": f"خطا در پردازش فایل: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
