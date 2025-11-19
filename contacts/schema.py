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





get_contact_stats_schema = extend_schema(
    tags=['Contacts', 'Statistics'],
    summary="Get contact statistics",
    description="Retrieve per-contact statistics, such as number of calls, answered calls, etc.",
    responses={
        200: OpenApiResponse(ContactStatsSerializer, description="Detailed contact statistics."),
        400: OpenApiResponse(description="Invalid contact data."),
    }
)

request_new_contact_schema = extend_schema(
    summary="Request a new contact for a project",
    description=(
        "Assigns a free contact from the selected project to the authenticated user. "
        "The user must have caller, project admin, or admin permissions."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The ID of the project for which a contact should be assigned.",
                    "example": 42,
                }
            },
            "required": ["project_id"],
        }
    },
    responses={
        200: OpenApiResponse(
            description="Successfully assigned a new contact.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "A new contact has been successfully assigned to you."}
                )
            ],
        ),
        400: OpenApiResponse(
            description="Project ID missing or invalid.",
            examples=[
                OpenApiExample(
                    "Missing ID",
                    value={"detail": "Project ID is required."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="No available contacts or project not found.",
            examples=[
                OpenApiExample(
                    "No Contacts",
                    value={"detail": "No available contacts to assign at the moment."}
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

release_contact_schema = extend_schema(
    tags=['Contacts', 'Release'],
    summary="آزاد کردن مخاطب",
    description=(
        "این عملیات برای آزاد کردن یک مخاطب تخصیص داده شده توسط تماس‌گیرنده یا ادمین است. "
        "مخاطب پس از آزاد شدن، به لیست عمومی مخاطبین بازمی‌گردد."
    ),
    parameters=[
        OpenApiParameter(
            name="contact_id",
            description="شناسه مخاطب که باید آزاد شود",
            required=True,
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="مخاطب با موفقیت آزاد شد و به لیست عمومی بازگشت.",
            examples=[
                OpenApiExample(
                    "Success",
                    value={"detail": "مخاطب با موفقیت آزاد شد و به لیست عمومی بازگشت."}
                )
            ],
        ),
        403: OpenApiResponse(
            description="دسترسی غیرمجاز. کاربر اجازه آزاد کردن این مخاطب را ندارد.",
            examples=[
                OpenApiExample(
                    "Forbidden",
                    value={"detail": "شما اجازه آزاد کردن این مخاطب را ندارید."}
                )
            ],
        ),
        404: OpenApiResponse(
            description="مخاطب یافت نشد.",
            examples=[
                OpenApiExample(
                    "Not Found",
                    value={"detail": "مخاطب مورد نظر یافت نشد."}
                )
            ],
        ),
    },
)