from drf_spectacular.utils import (OpenApiExample, OpenApiParameter,
                                   OpenApiResponse, extend_schema, OpenApiTypes, extend_schema_view)

from .serializers import ProjectMembershipSerializer, ProjectSerializer, QuestionSerializer, AnswerChoiceSerializer

# general schema for project management
project_schema = extend_schema(
    tags=["Projects"],
    description="Manage projects: view, create, edit, and ....."
)

# =====================================================
# --- ProjectViewSet Schemas
# =====================================================

project_list_schema = extend_schema(
    summary="List all projects",
    description="Returns all projects the authenticated user has access to. Superusers see all projects.",
    responses={200: ProjectSerializer(many=True)},
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Project list example",
            value=[
                {
                    "id": 1,
                    "name": "Customer Satisfaction Survey",
                    "description": "Survey project for Q1 2025.",
                    "status": "active",
                    "created_by": {
                        "id": 3,
                        "username": "admin",
                        "email": "admin@example.com"
                    },
                    "show": True,
                    "call_answers_summary": [],
                    "persian_updated_at": "1404-02-12",
                    "persian_created_at": "1404-02-11",
                    "project_statistics": {
                        "total_calls": 42,
                        "completed_calls": 36
                    }
                }
            ],
            response_only=True,
        ),
    ],
)

project_create_schema = extend_schema(
    summary="Create a new project",
    description="Creates a new project if the user has permission. Automatically assigns the creator as admin.",
    request=ProjectSerializer,
    responses={
        201: ProjectSerializer,
        403: OpenApiResponse(description="Not allowed to create project."),
    },
    examples=[
        OpenApiExample(
            "Example Request",
            summary="Example project creation body",
            value={
                "name": "New Marketing Campaign",
                "description": "Outbound call campaign for lead collection.",
                "status": "draft",
                "created_by_id": 3,
                "show": True
            },
            request_only=True,
        ),
        OpenApiExample(
            "Example Response",
            summary="Example response after creating project",
            value={
                "id": 7,
                "name": "New Marketing Campaign",
                "description": "Outbound call campaign for lead collection.",
                "status": "draft",
                "created_by": {
                    "id": 3,
                    "username": "admin",
                    "email": "admin@example.com"
                },
                "show": True,
                "call_answers_summary": [],
                "persian_updated_at": "1404-02-12",
                "persian_created_at": "1404-02-12",
                "project_statistics": {
                    "total_calls": 0,
                    "completed_calls": 0
                }
            },
            response_only=True,
        ),
    ],
)

check_user_role_schema = extend_schema(
    summary="Check user's role in a project",
    description="Checks a user's role in a specified project.",
    parameters=[
        OpenApiParameter(name="project_id",
                         description="Project ID", required=True, type=int),
        OpenApiParameter(name="user_id", description="User ID",
                         required=True, type=int),
    ],
    responses={
        200: ProjectMembershipSerializer,
        400: OpenApiResponse(description="Missing parameters."),
        404: OpenApiResponse(description="Membership not found."),
    },
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Successful role lookup",
            value={
                "id": 5,
                "project_id": 2,
                "user": {
                    "id": 10,
                    "username": "reza",
                    "email": "reza@example.com"
                },
                "role": "member",
                "assigned_at": "2025-04-20T10:12:00Z"
            },
            response_only=True,
        )
    ],
)

caller_performance_schema = extend_schema(
    summary="Get caller performance report",
    description="Returns a performance report for all callers in the project.",
    responses={200: OpenApiResponse(
        description="Report successfully generated.")},
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Performance report example",
            value={
                "project_id": 3,
                "project_name": "Customer Feedback Campaign",
                "callers": [
                    {"caller_id": 7, "name": "Sara",
                     "total_calls": 42, "success_rate": 85.5},
                    {"caller_id": 9, "name": "Ali",
                     "total_calls": 37, "success_rate": 78.0},
                ],
            },
            response_only=True,
        )
    ],
)

# =====================================================
# --- ProjectMembershipApiListView Schemas
# =====================================================

project_membership_list_schema = extend_schema(
    tags=['Projects'],
    summary="List project memberships",
    description="Lists all project memberships. You can filter by project using the `project_id` query parameter.",
    parameters=[
        OpenApiParameter(
            name="project_id", description="Optional project ID filter", required=False, type=int)
    ],
    responses={200: ProjectMembershipSerializer(many=True)},
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Membership list example",
            value=[
                {
                    "id": 3,
                    "project_id": 1,
                    "user": {"id": 10, "username": "amir", "email": "amir@example.com"},
                    "role": "admin",
                    "assigned_at": "2025-03-11T09:40:00Z"
                },
                {
                    "id": 4,
                    "project_id": 1,
                    "user": {"id": 11, "username": "fatemeh", "email": "fatemeh@example.com"},
                    "role": "member",
                    "assigned_at": "2025-03-12T10:00:00Z"
                }
            ],
            response_only=True,
        )
    ],
)

# =====================================================
# --- CallerImportView Schema
# =====================================================

caller_import_schema = extend_schema(
    tags=['Projects'],
    summary="Import callers from Excel",
    description="Upload an Excel file containing caller data and import them into the specified project.",
    parameters=[
        OpenApiParameter(
            name="project_id", description="Project ID to import into", required=True, type=int)
    ],
    request={
        "multipart/form-data": {
            "file": {
                "type": "string",
                "format": "binary",
                "description": "Excel file containing caller data"
            }
        }
    },
    responses={
        201: OpenApiResponse(description="Callers successfully imported."),
        400: OpenApiResponse(description="File not received or invalid."),
    },
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Successful import response",
            value={
                "message": "25 callers added.",
                "created_count": 25,
                "contacts": [
                    {"name": "Ali Ahmadi", "phone": "09121234567"},
                    {"name": "Sara Rahimi", "phone": "09351234567"},
                ],
                "project": "Customer Survey Project",
            },
            response_only=True,
        )
    ],
)

# =====================================================
# --- toggle_user_role Schema
# =====================================================

toggle_user_role_schema = extend_schema(
    tags=['Projects'],
    summary="Toggle user role in project",
    description="Toggles a user's role in a project (e.g. between 'admin' and 'member').",
    parameters=[
        OpenApiParameter(name="project_id",
                         description="Project ID", required=True, type=int),
        OpenApiParameter(name="user_id", description="User ID",
                         required=True, type=int),
    ],
    responses={
        200: OpenApiResponse(description="Role toggled successfully."),
        400: OpenApiResponse(description="Error toggling role."),
    },
    examples=[
        OpenApiExample(
            "Example Response",
            summary="Role toggle success example",
            value={
                "message": "User role changed successfully.",
                "user_id": 11,
                "username": "amir",
                "full_name": "Amir Rezaei",
                "old_role": "member",
                "new_role": "admin",
                "new_role_display": "Project Administrator"
            },
            response_only=True,
        )
    ],
)

# =========================
# Question & AnswerChoice Schemas
# =========================

question_schemas = extend_schema_view(
    # List questions of a project
    list=extend_schema(
        tags=["Q&A"],
        summary="List all questions for a project",
        description="Retrieve all questions for a given project, including their answer choices.",
        parameters=[
            OpenApiParameter(
                name='project_pk',
                description='ID of the project whose questions are being retrieved.',
                required=True,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response='QuestionSerializer',
                description="List of questions with their answer choices."
            ),
            404: OpenApiResponse(description="Project not found.")
        }
    ),
    retrieve=extend_schema(
        tags=["Q&A"],
        summary="Retrieve a single question",
        responses={200: QuestionSerializer}
    ),
    # Create a new question
    create=extend_schema(
        tags=['Q&A'],
        summary="Create a new question for a project",
        description="Automatically assigns the question to the project specified in the URL.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text of the question.",
                             "example": "What is your favorite color?"},
                    "is_active": {"type": "boolean", "description": "Is the question active?", "example": True},
                },
                "required": ["text"],
            }
        },
        responses={
            201: OpenApiResponse(
                response='QuestionSerializer',
                description="Question created successfully."
            ),
            400: OpenApiResponse(description="Invalid data provided."),
        }
    ),
    update=extend_schema(
        tags=["Q&A"],
        summary="Update a question",
        responses={200: QuestionSerializer}
    ),
    partial_update=extend_schema(
        tags=["Q&A"],
        summary="Partially update a question",
        responses={200: QuestionSerializer}
    ),
    destroy=extend_schema(
        tags=["Q&A"],
        summary="Delete a question",
        responses={204: OpenApiResponse(description="Question deleted")}
    ),
)

answer_choice_schemas = extend_schema_view(
    tags=["Q&A"],
    list=extend_schema(
        tags=["Q&A"],
        summary="List answer choices of a question",
        responses=AnswerChoiceSerializer,
    ),
    create=extend_schema(
        tags=["Q&A"],
        summary="Create a new answer choice",
        request=AnswerChoiceSerializer,
        responses=AnswerChoiceSerializer,
    ),
    retrieve=extend_schema(
        tags=["Q&A"],
        summary="Retrieve a single answer choice",
        responses=AnswerChoiceSerializer,
    ),
    update=extend_schema(
        tags=["Q&A"],
        summary="Update an existing answer choice",
        request=AnswerChoiceSerializer,
        responses=AnswerChoiceSerializer,
    ),
    partial_update=extend_schema(
        tags=["Q&A"],
        summary="Partially update an existing answer choice",
        request=AnswerChoiceSerializer,
        responses=AnswerChoiceSerializer,
    ),
    destroy=extend_schema(
        tags=["Q&A"],
        summary="Delete an answer choice",
        responses=OpenApiResponse(description="Answer choice deleted successfully"),
    ),
)
