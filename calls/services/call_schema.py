from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiTypes,
    OpenApiResponse,
    extend_schema_view,
)

from calls.serializers import CallSerializer

# General schema for call management
call_schema = extend_schema(
    tags=["Calls"],
    description="Manage calls: view, create, edit, and submit feedback."
)

# Filter schema based on project
project_filter_schema = extend_schema(
    tags=["Calls"],
    parameters=[
        OpenApiParameter("project_id", str, description="Filter calls by project ID", required=False),
    ],
    description="Display calls based on user permissions and optionally filter by project ID."
)

# Schema → Create a new call
call_create_detail_schema = extend_schema(
    description="Create a new call with full call details.",
    request=CallSerializer,
    responses={201: CallSerializer},
    examples=[
        OpenApiExample(
            name="New Call Example",
            summary="Example of a new call",
            value={
                "contact_id": 5,
                "project_id": 3,
                "status": "completed",
                "call_result": "successful",
                "notes": "The call was successfully completed.",
                "duration": 120
            },
            response_only=False
        )
    ]

)

schema_call_excel = extend_schema_view(
    list=extend_schema(
        tags=["Calls"],
        summary="Download call report as XLSX",
        description=(
            "Export all calls visible to the user in Excel format. "
            "Admins get all calls, project members get calls only from their projects."
        ),
        responses={
            200: {
                "description": "XLSX file download",
                "content": {
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
                }
            },
            403: {"description": "Permission denied"}
        }
    ),
    retrieve=extend_schema(
        tags=["Calls"],
        summary="Retrieve call details as XLSX",
        description=(
            "Export a single call's details in Excel format. "
            "Admins and project members can retrieve based on permissions."
        ),
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="XLSX file download"
            ),
            403: OpenApiResponse(description="Permission denied"),
            404: OpenApiResponse(description="Call not found")
        }
    )
)
