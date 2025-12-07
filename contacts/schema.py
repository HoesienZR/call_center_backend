from drf_spectacular.utils import (
    extend_schema_view,
    extend_schema,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample
)

from contacts.serializers import ContactSerializer, ContactStatsSerializer

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

    # ------------------ FILTER BY STATUS ------------------
    filter_by_status=extend_schema(
        tags=["Contacts"],
        summary="Filter contacts by status",
        parameters=[
            OpenApiParameter(
                name="status",
                description="Status to filter contacts",
                required=True,
                type=str,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={200: ContactSerializer(many=True), 400: OpenApiResponse(description="Status is required")}
    ),

    # ------------------ FILTER BY PROJECT ------------------
    filter_by_project=extend_schema(
        tags=["Contacts"],
        summary="Filter contacts by project",
        parameters=[
            OpenApiParameter(
                name="project_id",
                description="Project ID to filter contacts",
                required=True,
                type=int,
                location=OpenApiParameter.QUERY
            )
        ],
        responses={200: ContactSerializer(many=True), 400: OpenApiResponse(description="Project ID is required")}
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

    # ------------------ CONTACT STATS ------------------
    get_contact_stats=extend_schema(
        tags=["Contacts"],
        summary="Get contact stats",
        description="Return statistics related to a specific contact.",
        responses={200: ContactStatsSerializer}
    ),
)

# ------------------ REQUEST NEW CONTACT APIView ------------------
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

# ------------------ CONTACT IMPORT ------------------
schema_contact_import = extend_schema(
    tags=['Contacts'],
    summary="Import contacts from Excel",
    description="Upload an Excel or CSV file to add new contacts to a project. "
                "If the caller exists, it will be assigned automatically.",
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {'type': 'string', 'format': 'binary'}
            },
            'required': ['file']
        }
    },
    responses={
        201: OpenApiResponse(
            description="Contacts imported successfully",
            examples=[
                OpenApiExample(
                    name="Success Example",
                    summary="Example of successful contact import",
                    value={
                        "message": "5 مخاطب با موفقیت اضافه شد.",
                        "created_count": 5,
                        "contacts": ["09123456789", "09121234567"],
                        "project": "Excel Project"
                    }
                )
            ]
        ),
        400: OpenApiResponse(
            description="Bad request, e.g. missing required columns or file not uploaded",
            examples=[
                OpenApiExample(
                    name="Missing Column",
                    value={"error": "ستون 'contact_phone' در فایل موجود نیست."}
                ),
                OpenApiExample(
                    name="No File",
                    value={"error": "فایل اکسل ارسال نشده است."}
                )
            ]
        )
    }
)
