from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
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
            "New Call Example",
            value={
                "contact_id": 5,
                "project_id": 3,
                "status": "completed",
                "call_result": "successful",
                "notes": "The call was successfully completed.",
                "duration": 120
            }
        )
    ]
)

# Schema → Edit call and submit change history
call_edit_changesubmit_schema = extend_schema(
    description="Edit an existing call and record all field change history.",
    request=CallSerializer,
    responses={200: CallSerializer},
    examples=[
        OpenApiExample(
            "Edit Call Example",
            value={"notes": "Customer was informed.", "edit_reason": "Updated notes"}
        )
    ]
)


