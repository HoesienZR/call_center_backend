from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from contacts.serializers import ContactSerializer, ContactStatsSerializer

filter_contact_by_status_and_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by status and project",
    description=(
        "Returns a list of contacts filtered by both `status` and `project_id`. "
        "Includes assigned caller info, related project, and any notes associated with each contact."
    ),
    parameters=[
        OpenApiParameter(name='status', description='Filter contacts by their call status', required=True, type=OpenApiTypes.STR),
        OpenApiParameter(name='project_id', description='Filter contacts within a specific project', required=True, type=OpenApiTypes.INT),
    ],
    responses={
        200: OpenApiResponse(
            response=ContactSerializer,
            description="A list of contacts filtered by project and status."
        ),
        400: OpenApiResponse(description="Missing or invalid query parameters."),
    }
)

filter_contact_by_status_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by status",
    description="Returns all contacts that match a given status value.",
    parameters=[
        OpenApiParameter(name='status', description='The status of contacts to filter by', required=True, type=OpenApiTypes.STR),
    ],
    responses={
        200: OpenApiResponse(ContactSerializer, description="Filtered contact list."),
        400: OpenApiResponse(description="Missing status parameter.")
    }
)


filter_contact_by_project_schema = extend_schema(
    tags=['Contacts', 'Filter'],
    summary="Filter contacts by project",
    description="Returns all contacts that belong to the specified project ID.",
    parameters=[
        OpenApiParameter(name='project_id', description='The ID of the project to filter by', required=True, type=OpenApiTypes.INT),
    ],
    responses={
        200: OpenApiResponse(ContactSerializer, description="List of contacts in the given project."),
        400: OpenApiResponse(description="Project ID not provided or invalid."),
    }
)


request_new_contact_schema = extend_schema(
    tags=['Contacts', 'Caller'],
    summary="Request a new contact assignment",
    description=(
        "Allows a caller to request a new available contact within a project. "
        "If successful, the contact will be assigned to the current user."
    ),
    request=None,
    parameters=[
        OpenApiParameter(name='project_id', description='The project ID from which to assign a new contact', required=True, type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
    ],
    responses={
        200: OpenApiResponse(description="A new contact was assigned."),
        403: OpenApiResponse(description="User is not a member of the project."),
        404: OpenApiResponse(description="No available contacts or project not found."),
        400: OpenApiResponse(description="Missing project_id parameter."),
    },
)

release_contact_schema = extend_schema(
    tags=['Contacts', 'Caller'],
    summary="Release an assigned contact",
    description=(
        "Allows a caller or admin to release a contact, making it available for reassignment."
    ),
    responses={
        200: OpenApiResponse(description="Contact released successfully."),
        403: OpenApiResponse(description="User not authorized to release this contact."),
    },
)


get_contact_stats_schema = extend_schema(
    tags=['Contacts', 'Statistics'],
    summary="Get contact statistics",
    description="Retrieve per-contact statistics, such as number of calls, answered calls, etc.",
    responses={
        200: OpenApiResponse(ContactStatsSerializer, description="Detailed contact statistics."),
        400: OpenApiResponse(description="Invalid contact data."),
    }
)
