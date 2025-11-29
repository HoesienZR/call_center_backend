from drf_spectacular.types import OpenApiTypes

from contacts.serializers import ContactSerializer, ContactStatsSerializer
from calls.serializers import CallSerializer
from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiResponse,
    OpenApiExample
)

contact_schema = extend_schema_view(

    # ------------------ LIST ------------------
    list=extend_schema(
        tags=["Contacts"],
        summary="List contacts",
        description="List all contacts visible to the user depending on project role.",
        responses={200: ContactSerializer(many=True)}
    ),

    # ------------------ RETRIEVE ------------------
    retrieve=extend_schema(
        tags=["Contacts"],
        summary="Retrieve contact details",
        responses={200: ContactSerializer}
    ),

    # ------------------ CREATE ------------------
    create=extend_schema(
        tags=["Contacts"],
        summary="Create a new contact",
        responses={201: ContactSerializer}
    ),

    # ------------------ UPDATE ------------------
    update=extend_schema(
        tags=["Contacts"],
        summary="Update a contact",
        responses={200: ContactSerializer}
    ),

    # ------------------ PARTIAL UPDATE ------------------
    partial_update=extend_schema(
        tags=["Contacts"],
        summary="Partially update a contact",
        responses={200: ContactSerializer}
    ),

    # ------------------ DELETE ------------------
    destroy=extend_schema(
        tags=["Contacts"],
        summary="Delete a contact",
        responses={204: OpenApiResponse(description="Contact deleted")}
    ),

    # ------------------ FILTER BY STATUS + PROJECT ------------------
    filter_contact_by_status_and_project=extend_schema(
        tags=["Contacts"],
        summary="Filter contacts by status & project",
        parameters=[
            {
                "name": "status",
                "required": True,
                "in": "query",
                "schema": {"type": "string"},
            },
            {
                "name": "project_id",
                "required": True,
                "in": "query",
                "schema": {"type": "integer"},
            }
        ],
        responses={200: ContactSerializer(many=True)}
    ),

    # ------------------ FILTER BY STATUS ------------------
    filter_contact_by_status=extend_schema(
        tags=["Contacts"],
        summary="Filter contacts by status",
        parameters=[
            {
                "name": "status",
                "required": True,
                "in": "query",
                "schema": {"type": "string"},
            }
        ],
        responses={200: ContactSerializer(many=True)}
    ),

    # ------------------ FILTER BY PROJECT ------------------
    filter_contact_by_project=extend_schema(
        tags=["Contacts"],
        summary="Filter contacts by project",
        parameters=[
            {
                "name": "project_id",
                "required": True,
                "in": "query",
                "schema": {"type": "integer"},
            }]
        ,
        responses={200: ContactSerializer(many=True)}
    ),

    # ------------------ REQUEST NEW CONTACT ------------------
    request_new_contact=extend_schema(
        tags=["Contacts"],
        summary="Request a new contact",
        description="Caller requests a new available contact from a project.",
        request={
            "application/json": {
                "type": "object",
                "properties": {"project_id": {"type": "integer"}},
                "required": ["project_id"],
            }
        },
        responses={200: OpenApiResponse(description="New contact assigned")}
    ),

    # ------------------ RELEASE CONTACT ------------------
    release_contact=extend_schema(
        tags=["Contacts"],
        summary="Release a contact",
        description="Caller/Admin can release a contact, returning it to the pool.",
        responses={200: OpenApiResponse(description="Contact released")}
    ),

    # ------------------ SUBMIT CALL ------------------
    submit_call=extend_schema(
        tags=["Calls"],
        summary="Submit a call for a contact",
        request=CallSerializer,
        responses={200: OpenApiResponse(description="Call submitted")}
    ),

    # ------------------ CONTACT STATS ------------------
    get_contact_stats=extend_schema(
        tags=["Contacts"],
        summary="Get contact stats",
        description="Return statistics related to a specific contact.",
        responses={200: ContactStatsSerializer}
    ),

)


request_new_contact_schema = extend_schema(
    tags=["Contacts"],
    summary="Request a new contact (APIView)",
    description="Assign an available contact to the caller if possible.",
    request={
        "application/json": {
            "type": "object",
            "properties": {"project_id": {"type": "integer"}},
            "required": ["project_id"],
        }
    },
    responses={
        200: OpenApiResponse(description="A new contact was assigned"),
        404: OpenApiResponse(description="No contacts available"),
        400: OpenApiResponse(description="Invalid request")
    }
)
