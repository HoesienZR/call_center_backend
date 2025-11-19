import logging
from django.db import transaction
from django.db.models import Q, Count
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets
from rest_framework.views import APIView

from call_center_backend import settings
from core.utils import validate_phone_number, normalize_phone_number
from .utils import assign_available_contact
from projects.models import ProjectMembership
from .models import Project, Contact
from .permission import IsProjectCaller, IsProjectAdmin, ReleaseContactPermission
from .serializers import ContactSerializer, ContactStatsSerializer
from .schema import (
    filter_contact_by_status_and_project_schema,
    release_contact_schema,
    get_contact_stats_schema,
    filter_contact_by_project_schema,
    filter_contact_by_status_schema,
    request_new_contact_schema,
)

# تنظیم logger
logger = logging.getLogger(__name__)

User = settings.AUTH_USER_MODEL


class ContactViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contacts within projects.
    """
    queryset = Contact.objects.select_related("project", "assigned_caller").prefetch_related('calls')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsProjectAdmin | IsAdminUser | IsProjectCaller]

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_queryset(self):
        """
        Custom queryset for filtering contacts based on user permissions.
        """
        user = self.request.user
        base_qs = Contact.objects.select_related("project", "assigned_caller").prefetch_related("calls")

        # Superusers can access all contacts
        if user.is_superuser:
            qs = base_qs
        else:
            # Get user projects
            user_projects = Project.objects.filter(member=user)
            if ProjectMembership.objects.filter(project__in=user_projects, user=user, role='admin').exists():
                qs = base_qs.filter(project__in=user_projects)
            else:
                qs = base_qs.filter(assigned_caller=user)

        # Annotate the contacts with call stats
        qs = qs.annotate(
            total_calls=Count('calls', distinct=True),
            answered_calls=Count('calls', filter=Q(calls__status='answered'), distinct=True),
            not_answered_calls=Count('calls', filter=Q(calls__status='no_answer'), distinct=True),
            interested_calls=Count('calls', filter=Q(calls__call_result='interested'), distinct=True),
            not_interested_calls=Count('calls', filter=Q(calls__call_result='not_interested'), distinct=True),
            no_time_calls=Count('calls', filter=Q(calls__call_result='no_time'), distinct=True),
        )
        return qs

    def perform_create(self, serializer):
        """
        Create a new contact, and assign it to the caller if applicable.
        """
        project = serializer.validated_data['project']
        user = self.request.user

        # Automatically assign the contact to the caller if no caller is specified
        if not serializer.validated_data.get('assigned_caller'):
            try:
                membership = ProjectMembership.objects.get(project=project, user=user)
                if membership.role == 'caller':
                    serializer.validated_data['assigned_caller'] = user
            except ProjectMembership.DoesNotExist:
                pass

        serializer.save(created_by=user)

    @filter_contact_by_status_and_project_schema
    @action(detail=False, methods=['get'], url_path="filter_contact_by_status_and_project", permission_classes=[])
    def filter_contact_by_status_and_project(self, request):
        """
        Filter contacts by project ID and status.
        """
        contact_status = self.request.GET.get('status')
        project_id = self.request.GET.get('project_id')
        if contact_status is None or project_id is None:
            return Response({'detail': 'Both status and project_id must be provided'},
                            status=status.HTTP_400_BAD_REQUEST)

        contacts_filtered_by_project_and_status = self._filter_contacts(project_id=project_id,
                                                                        contact_status=contact_status)
        serializer = self.get_serializer(contacts_filtered_by_project_and_status, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @filter_contact_by_status_schema
    @action(detail=False, methods=['get'], url_path="filter_contact_by_status")
    def filter_contact_by_status(self, request):
        """
        Filter contacts by their status.
        """
        contact_status = self.request.GET.get('status')
        if contact_status is None:
            return Response({'detail': 'status must be set'}, status=status.HTTP_400_BAD_REQUEST)

        contact_filter_by_status = self._filter_contacts(contact_status=contact_status)
        serializer = self.get_serializer(contact_filter_by_status, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @filter_contact_by_project_schema
    @action(detail=False, methods=['get'], url_path="filter_contact_by_project")
    def filter_contact_by_project(self, request):
        """
        Filter contacts by project ID.
        """
        project_id = self.request.GET.get('project_id')
        if project_id is None:
            return Response({'detail': "Invalid or missing project ID"}, status=status.HTTP_400_BAD_REQUEST)

        contact_filter_by_project = self._filter_contacts(project_id=project_id)
        serializer = self.get_serializer(contact_filter_by_project, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='request_new')
    def request_new_contact(self, request):
        """
        Request a new contact for a caller.
        """
        project_id = request.data.get('project_id')
        if not project_id:
            return Response({"detail": "Project ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)

            if not ProjectMembership.objects.filter(project=project, user=request.user).exists():
                return Response({"detail": "You are not a member of this project."}, status=status.HTTP_403_FORBIDDEN)

            available_contact = Contact.objects.filter(
                project=project,
                assigned_caller__isnull=True,
                call_status='pending',
                is_active=True
            ).first()

            if available_contact:
                available_contact.assigned_caller = request.user
                available_contact.save()
                return Response(
                    {"detail": "A new contact has been assigned to you."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"detail": "No available contacts to assign."},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Project.DoesNotExist:
            return Response({"detail": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

    @release_contact_schema
    @action(detail=True, methods=['post'], url_path='release', permission_classes=[ReleaseContactPermission])
    def release_contact(self, request):
        """
        Release a contact by the caller or admin.
        """
        contact = self.get_object()
        user = request.user

        if contact.assigned_caller == user:
            contact.assigned_caller = None
            contact.save()

            return Response(
                {"detail": "Contact has been successfully released and returned to the pool."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "You are not authorized to release this contact."},
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=["post"], url_path="submit-call")
    def submit_call(self, request, pk=None):
        """
        Submit a new call for a contact.
        """
        contact = self.get_object()

        if not contact.assigned_caller == request.user:
            return Response({"detail": "You are not authorized to submit a call for this contact."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = CallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the call and update contact status
        call = serializer.save(
            caller=request.user,
            contact=contact,
            project=contact.project
        )

        call_result = serializer.validated_data.get('call_result')
        status_map = {
            'answered': 'contacted',
            'callback_requested': 'follow_up',
            'not_interested': 'not_interested',
            'wrong_number': 'not_interested',
        }

        # Update the contact's status based on the call result
        contact.call_status = status_map.get(call_result, contact.call_status)
        contact.save()

        return Response({"detail": "Call has been successfully submitted."}, status=status.HTTP_200_OK)

    @get_contact_stats_schema
    @action(detail=True, methods=['get'], url_path='stats')
    def get_contact_stats(self, request, pk=None):
        """
        Get statistics for a specific contact.
        """
        contact = self.get_object()
        serializer = ContactStatsSerializer(contact, context={'request': request})
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _filter_contacts(self, project_id=None, contact_status=None):
        """
        Helper method to filter contacts based on project and status.
        """
        qs = self.get_queryset()
        if project_id:
            qs = qs.filter(project_id=project_id)
        if contact_status:
            qs = qs.filter(call_status=contact_status)
        return qs


class RequestNewContactView(APIView):
    """
    API view for requesting a new contact for a caller.
    """
    permission_classes = [IsAuthenticated, IsProjectCaller | IsAdminUser | IsProjectAdmin]

    @request_new_contact_schema
    def post(self, request):
        project_id = request.data.get("project_id")
        if not project_id:
            return Response(
                {"detail": "Project ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        project = get_object_or_404(Project, id=project_id)

        if assign_available_contact(project, request.user):
            return Response(
                {"detail": "A new contact has been successfully assigned to you."},
                status=status.HTTP_200_OK
            )

        return Response(
            {"detail": "No available contacts to assign at the moment."},
            status=status.HTTP_404_NOT_FOUND
        )
