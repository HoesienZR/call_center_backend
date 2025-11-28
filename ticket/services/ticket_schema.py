from drf_spectacular.utils import extend_schema, extend_schema_view
from ticket.models import Ticket
from ticket.serializers import TicketSerializer

ticket_all_schema = extend_schema_view(
    list=extend_schema(
        summary="List Tickets",
        description="Returns the list of tickets belonging to the user (or all tickets depending on your logic).",
        tags=["Tickets"],
        responses={200: TicketSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Ticket Details",
        description="Retrieve the details of a ticket by its ID.",
        tags=["Tickets"],
        responses={200: TicketSerializer},
    ),
    create=extend_schema(
        summary="Create New Ticket",
        description="Create a new ticket. The 'user' field will be automatically set from the logged-in user.",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={201: TicketSerializer},
    ),
    update=extend_schema(
        summary="Update Ticket",
        description="Fully update a ticket with new data.",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={200: TicketSerializer},
    ),
    partial_update=extend_schema(
        summary="Partial Ticket Update",
        description="Partially update a ticket with the provided fields.",
        tags=["Tickets"],
        request=TicketSerializer,
        responses={200: TicketSerializer},
    ),
    destroy=extend_schema(
        summary="Delete Ticket",
        description="Delete a ticket by its ID.",
        tags=["Tickets"],
        responses={204: None},
    ),
)
