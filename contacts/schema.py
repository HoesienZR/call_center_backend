from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse

from contacts.serializers import ContactSerializer, ContactStatsSerializer

# Filter contacts by status + project
filter_contact_by_status_and_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by status and project",
    description=(
        "Returns a list of contacts filtered by `status` and `project_id`. "
        "The list includes assigned caller information, project details, and any related notes."
    ),
    parameters=[
        OpenApiParameter(
            name='status',
            description='Filter contacts by their call status.',
            required=True,
            type=OpenApiTypes.STR
        ),
        OpenApiParameter(
            name='project_id',
            description='Filter contacts belonging to a specific project.',
            required=True,
            type=OpenApiTypes.INT
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="List of contacts filtered by status and project."
        ),
        400: OpenApiResponse(description="Missing or invalid query parameters.")
    }
)

# Filter contacts by status only
filter_contact_by_status_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by status",
    description="Returns all contacts that match the given status.",
    parameters=[
        OpenApiParameter(
            name='status',
            description='The status used to filter contacts.',
            required=True,
            type=OpenApiTypes.STR
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="List of filtered contacts."
        ),
        400: OpenApiResponse(description="Status parameter is missing.")
    }
)

# Filter contacts by project only
filter_contact_by_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by project",
    description="Returns all contacts belonging to the specified project.",
    parameters=[
        OpenApiParameter(
            name='project_id',
            description='The project ID used for filtering.',
            required=True,
            type=OpenApiTypes.INT
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="List of contacts belonging to the specified project."
        ),
        400: OpenApiResponse(description="Missing or invalid project ID.")
    }
)

# Get contact statistics
get_contact_stats_schema = extend_schema(
    tags=['Contacts', 'Statistics'],
    summary="Retrieve contact statistics",
    description="Returns statistics for a contact such as total calls, answered calls, and more.",
    responses={
        200: OpenApiResponse(
            response=ContactStatsSerializer,
            description="Detailed contact statistics."
        ),
        400: OpenApiResponse(description="Invalid contact data.")
    }
)

# Request a new contact for a project
request_new_contact_schema = extend_schema(
    summary="Request a new contact for a project",
    description=(
        "Assigns an available contact from the selected project to the authenticated user. "
        "The user must be a caller, project admin, or system admin."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "ID of the project to request a new contact from.",
                    "example": 42,
                }
            },
            "required": ["project_id"],
        }
    },
    responses={
        200: OpenApiResponse(
            description="A new contact was successfully assigned to you.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "A new contact was successfully assigned to you."}
                )
            ],
        ),
        400: OpenApiResponse(
            description="Missing or invalid project ID.",
            examples=[
                OpenApiExample(
                    "Missing ID",
                    value={"detail": "Project ID is required."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="No available contact or project not found.",
            examples=[
                OpenApiExample(
                    "No Contacts",
                    value={"detail": "No free contact available for assignment."}
                )
            ],
        ),
    },
    parameters=[
        OpenApiParameter(
            name="Authorization",
            location=OpenApiParameter.HEADER,
            required=True,
            description="Bearer access token for authentication.",
            type=str,
        ),
    ],
)

# Release a contact
release_contact_schema = extend_schema(
    tags=['Contacts', 'Release'],
    summary="Release a contact",
    description=(
        "This operation releases a previously assigned contact. "
        "The contact becomes available again for other users."
    ),
    parameters=[
        OpenApiParameter(
            name="contact_id",
            description="ID of the contact to be released.",
            required=True,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="The contact was successfully released.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "The contact has been successfully released."}
                )
            ],
        ),
        403: OpenApiResponse(
            description="Unauthorized. The user is not allowed to release this contact.",
            examples=[
                OpenApiExample(
                    "Forbidden",
                    value={"detail": "You are not allowed to release this contact."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="The specified contact was not found.",
            examples=[
                OpenApiExample(
                    "Not Found",
                    value={"detail": "The contact was not found."}
                )
            ],
        ),
    },
)
