from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
    OpenApiResponse,
    extend_schema_view,
)

from calls.serializers import CallSerializer, CallEditHistorySerializer

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

# Schema → Submit feedback by the caller
caller_feedback_schema = extend_schema(
    description="Submit feedback on a call by the caller.",
    request={
        "type": "object",
        "properties": {
            "notes": {
                "type": "string",
                "example": "The customer did not answer.",
                "description": "A note or comment about the call result."
            },
            "status": {
                "type": "string",
                "example": "failed",
                "description": "The final call status (e.g. failed, completed)."
            }
        }
    },
    responses={200: CallSerializer}
)

# Schema → Submit detailed report
detailed_report_schema = extend_schema(
    description="Submit a detailed report for a call (suitable for full call summaries).",
    request={
        "type": "object",
        "properties": {
            "report_data": {
                "type": "object",
                "example": {"summary": "Discussion about a new contract."}
            },
            "call_status": {
                "type": "string",
                "example": "completed"
            }
        }
    },
    responses={200: CallSerializer}
)

# Schema → GET list of call edit histories
list_call_edit_history_schema = extend_schema(
    summary="List call edit history records",
    description="Retrieve a list of all call edit history records. Only admin users have access.",
    responses={
        200: OpenApiResponse(
            response=CallEditHistorySerializer,
            description="List of call edit history records.",
            examples=[
                OpenApiExample(
                    "Example Response",
                    value=[{
                        "id": 1,
                        "call": 101,
                        "edited_by": 5,
                        "edit_date": "2025-11-14T12:00:00Z",
                        "field_name": "status",
                        "old_value": "pending",
                        "new_value": "completed",
                        "edit_reason": "Approved by supervisor"
                    }]
                )
            ]
        ),
        403: OpenApiResponse(description="Forbidden"),
    }
)

# Schema → GET details of a specific call edit history record
retrieve_call_edit_history_schema = extend_schema(
    summary="Retrieve a call edit history record",
    description="Retrieve a single call edit history record by its ID.",
    responses={
        200: OpenApiResponse(
            response=CallEditHistorySerializer,
            description="Details of a call edit history record.",
            examples=[
                OpenApiExample(
                    "Example Response",
                    value={
                        "id": 1,
                        "call": 101,
                        "edited_by": 5,
                        "edit_date": "2025-11-14T12:00:00Z",
                        "field_name": "status",
                        "old_value": "pending",
                        "new_value": "completed",
                        "edit_reason": "Approved by supervisor"
                    }
                )
            ]
        ),
        404: OpenApiResponse(description="Record not found"),
        403: OpenApiResponse(description="Forbidden"),
    }
)

# Combined view schema for CallEditHistory endpoints
call_edit_history_schema = extend_schema_view(
    list=extend_schema(
        summary="List all call edit history records",
        description=(
            "Displays a list of all CallEditHistory records.\n"
            "Each record shows which field of a call was modified, by whom, when, "
            "and from which value to which new value."
        ),
        tags=["Call Edit History"],
        responses={200: CallEditHistorySerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Get details of a single call edit history record",
        description=(
            "Retrieve a single CallEditHistory record by its ID.\n"
            "Includes field name, old value, new value, editor, and edit timestamp."
        ),
        tags=["Call Edit History"],
        responses={200: CallEditHistorySerializer},
    ),
)
