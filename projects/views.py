import logging
import traceback

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import mixins, generics

from core.permissions import IsReadOnlyOrProjectAdmin, IsProjectAdmin
from .schema import (
    project_list_schema,
    project_create_schema,
    check_user_role_schema,
    caller_performance_schema,
    project_membership_list_schema,
    caller_import_schema,
    toggle_user_role_schema,
)
from .models import AnswerChoice, Project, ProjectMembership, Question
from .serializers import QuestionSerializer, AnswerChoiceSerializer, ProjectSerializer, ProjectMembershipSerializer
from .utils import (
    import_caller_from_excel,
    check_if_user_exist,
    check_if_project_membership_exist,
    toggle_user_project_membership_role
)

logger = logging.getLogger(__name__)


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsReadOnlyOrProjectAdmin]

    @project_list_schema
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @project_create_schema
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        """Return projects accessible to the authenticated user, with optimized prefetching."""
        user = self.request.user
        base_prefetch = [
            Prefetch('questions', queryset=Question.objects.prefetch_related('choices')),
            Prefetch(
                'calls__answers',
                queryset=CallAnswer.objects.select_related('selected_choice').prefetch_related(
                    Prefetch('question__choices')
                )
            )
        ]

        if user.is_superuser:
            return Project.objects.all().prefetch_related(*base_prefetch)

        return user.projects.distinct().prefetch_related(*base_prefetch)

    def perform_create(self, serializer):
        """Create a project and automatically assign the creator as project admin."""
        user = self.request.user
        if not user.can_create_projects:
            raise PermissionDenied("You do not have permission to create new projects.")
        with transaction.atomic():
            project = serializer.save(created_by=user)
            ProjectMembership.objects.create(project=project, user=user, role='admin')

    @check_user_role_schema
    @action(detail=False, methods=['get'], url_path='check-user-role', permission_classes=[IsAuthenticated])
    def check_user_role(self, request):
        """Check the role of a user in a project."""
        project_id = request.data.get('project_id')
        user_id = request.data.get('user_id')

        if not project_id:
            return self._error_response('Project ID is required')

        if not user_id:
            return self._error_response('User ID is required')

        try:
            project_membership = ProjectMembership.objects.get(project_id=project_id, user_id=user_id)
        except ProjectMembership.DoesNotExist:
            return self._error_response('membership not found', status=status.HTTP_404_NOT_FOUND)
        except ProjectMembership.MultipleObjectsReturned:
            return self._error_response("multiple roles returned", status=status.HTTP_400_BAD_REQUEST)

        serializer = ProjectMembershipSerializer(project_membership)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @caller_performance_schema
    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated, IsProjectAdmin])
    def caller_performance(self, request, pk=None):
        """Return caller performance report of the project."""
        project = self.get_object()
        report = project.get_caller_performance_report()
        return Response(report)

    def _error_response(self, message, status=status.HTTP_400_BAD_REQUEST):
        """Helper to return error responses."""
        return Response({'error': message}, status=status)


class ProjectMembershipApiListView(mixins.ListModelMixin, generics.GenericAPIView):
    queryset = ProjectMembership.objects.select_related("project", "user")
    serializer_class = ProjectMembershipSerializer

    @project_membership_list_schema
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        """Optionally filter memberships by project_id."""
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return self.queryset.filter(project_id=project_id)
        return self.queryset


class CallerImportView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @caller_import_schema
    def post(self, request, project_id):
        """
        Upload an Excel file and add new callers.
        If callers already exist, they will be assigned to the project.
        """
        project = get_object_or_404(Project, id=project_id)
        file_obj = request.FILES.get("file")

        if not file_obj:
            return self._error_response("Excel file was not received.", status=status.HTTP_400_BAD_REQUEST)

        try:
            created_contacts = import_caller_from_excel(file_obj, project)
            return Response(
                {
                    "message": f"{len(created_contacts)} callers were added",
                    "created_count": len(created_contacts),
                    "contacts": created_contacts,
                    "project": project.name,
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            traceback.print_exc()
            return self._error_response(f"Processing error: {str(e)}", status=status.HTTP_400_BAD_REQUEST)

    def _error_response(self, message, status=status.HTTP_400_BAD_REQUEST):
        """Helper to return error responses."""
        return Response({"error": message}, status=status)


@toggle_user_role_schema
@api_view(["GET"])
def toggle_user_role(request):
    """Toggle a user's role in a project."""
    try:
        project = check_if_user_exist(request.data.get('project_id'))
        user = check_if_user_exist(request.data.get('user_id'))
        project_membership = check_if_project_membership_exist(project=project, user=user)
        old_role, new_role = toggle_user_project_membership_role(
            project=project,
            user=user,
            project_membership=project_membership
        )
    except Exception as e:
        traceback.print_exc()
        return Response({"error": f"Processing error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    response_data = {
        'message': 'User role was successfully updated',
        'user_id': user.id,
        'username': user.username,
        'full_name': user.get_full_name(),
        'old_role': old_role,
        'new_role': new_role,
        'new_role_display': project_membership.get_role_display(),
    }
    return Response(response_data, status=status.HTTP_200_OK)


class QuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project questions."""
    serializer_class = QuestionSerializer
    permission_classes = [IsAuthenticated, IsProjectAdmin | IsAdminUser]

    def get_queryset(self):
        """Return all questions belonging to the project in the URL."""
        project_id = self.kwargs['project_pk']
        return Question.objects.filter(project_id=project_id).prefetch_related(
            Prefetch('choices', queryset=AnswerChoice.objects.all())
        )

    def perform_create(self, serializer):
        """Automatically assign the created question to the project."""
        project_id = self.kwargs['project_pk']
        serializer.save(project_id=project_id)


class AnswerChoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing answer choices of questions."""
    serializer_class = AnswerChoiceSerializer
    permission_classes = [IsAuthenticated, IsProjectAdmin | IsAdminUser]

    def get_queryset(self):
        """Return all answer choices belonging to the question in the URL."""
        question_id = self.kwargs['question_pk']
        return AnswerChoice.objects.filter(question_id=question_id)

    def perform_create(self, serializer):
        """Automatically assign the answer choice to its question."""
        question_id = self.kwargs['question_pk']
        serializer.save(question_id=question_id)
