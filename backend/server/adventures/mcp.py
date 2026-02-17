"""
MCP Tools for AdventureLog.

Provides AI agents with tools to interact with AdventureLog:
- search_items: Search locations, transportations, and lodging (own + public)
- get_item: Get full details of a single item
- list_items: List items by type (own + public)
- create_location: Create a new location
- create_transportation: Create a new transportation
- create_lodging: Create a new lodging
- edit_location: Edit a location (owner or collab on public)
- edit_transportation: Edit a transportation (owner or collab on public)
- edit_lodging: Edit a lodging (owner or collab on public)
- create_visit: Add a visit to an entity
- edit_visit: Edit an existing visit
- delete_visit: Delete a visit
- list_visits: List visits
- create_activity: Add an activity to a visit (no GPX)
- create_collection: Create a trip collection
- edit_collection: Edit a collection
- list_collections: List trip collections
- get_collection: Get full collection details with itinerary
- add_to_collection: Add an item to a collection
- share_collection: Share a collection with another user
- unshare_collection: Remove a user from a shared collection
- create_note: Create a note (optionally in a collection)
- edit_note: Edit a note
- delete_note: Delete a note
- list_notes: List notes
- create_checklist: Create a checklist with items
- edit_checklist: Edit a checklist and its items
- delete_checklist: Delete a checklist
- list_checklists: List checklists
- list_templates: List collection templates
- apply_template: Create a collection from a template
- reverse_geocode: Get address info from coordinates
- list_reference_types: List all available types
"""

from typing import Optional
from mcp_server import MCPToolset
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery


def _is_collaborative():
    """Check if collaborative mode is enabled."""
    from django.conf import settings
    return getattr(settings, 'COLLABORATIVE_MODE', False)


def _get_editable_item(model, item_id, user):
    """Get an item the user can edit: owned, or public in collaborative mode."""
    if _is_collaborative():
        return model.objects.get(Q(id=item_id) & (Q(user=user) | Q(is_public=True)))
    return model.objects.get(id=item_id, user=user)


class AdventureLogTools(MCPToolset):
    """MCP tools for AdventureLog."""

    def search_items(
        self,
        query: str,
        item_type: str = "all",
        limit: int = 10
    ) -> list:
        """
        Search for locations, transportations, or lodging.

        Args:
            query: Search text to find items by name, description, or location
            item_type: Type of item to search for. Options: "location", "transportation", "lodging", or "all"
            limit: Maximum number of results to return (default 10, max 50)

        Returns:
            List of matching items with basic info (id, name, type, description excerpt)
        """
        from adventures.models import Location, Transportation, Lodging

        user = self.request.user
        limit = min(limit, 50)
        results = []

        accessible = Q(user=user) | Q(is_public=True) | Q(collections__shared_with=user)

        if item_type in ("all", "location"):
            locations = Location.objects.annotate(
                search=SearchVector('name', 'description', 'location')
            ).filter(
                search=SearchQuery(query),
            ).filter(
                accessible
            ).distinct()[:limit]

            for loc in locations:
                results.append({
                    "type": "location",
                    "id": str(loc.id),
                    "name": loc.name,
                    "description": (loc.description or "")[:200],
                    "location": loc.location,
                    "is_public": loc.is_public,
                    "is_owner": loc.user == user,
                    "latitude": float(loc.latitude) if loc.latitude else None,
                    "longitude": float(loc.longitude) if loc.longitude else None,
                })

        if item_type in ("all", "transportation"):
            transportations = Transportation.objects.annotate(
                search=SearchVector('name', 'description', 'from_location', 'to_location', 'flight_number')
            ).filter(
                search=SearchQuery(query),
            ).filter(
                accessible
            ).distinct()[:limit]

            for t in transportations:
                results.append({
                    "type": "transportation",
                    "id": str(t.id),
                    "name": t.name,
                    "description": (t.description or "")[:200],
                    "transportation_type": t.type,
                    "from_location": t.from_location,
                    "to_location": t.to_location,
                    "is_public": t.is_public,
                    "is_owner": t.user == user,
                })

        if item_type in ("all", "lodging"):
            lodgings = Lodging.objects.annotate(
                search=SearchVector('name', 'description', 'location', 'reservation_number')
            ).filter(
                search=SearchQuery(query),
            ).filter(
                accessible
            ).distinct()[:limit]

            for l in lodgings:
                results.append({
                    "type": "lodging",
                    "id": str(l.id),
                    "name": l.name,
                    "description": (l.description or "")[:200],
                    "lodging_type": l.type,
                    "location": l.location,
                    "is_public": l.is_public,
                    "is_owner": l.user == user,
                    "latitude": float(l.latitude) if l.latitude else None,
                    "longitude": float(l.longitude) if l.longitude else None,
                })

        return results[:limit]

    def get_item(self, item_type: str, item_id: str) -> dict:
        """
        Get full details of a location, transportation, or lodging.

        Args:
            item_type: Type of item. Options: "location", "transportation", or "lodging"
            item_id: UUID of the item

        Returns:
            Full item details including visits, collections, and images
        """
        from adventures.models import Location, Transportation, Lodging
        from adventures.serializers import LocationSerializer, TransportationSerializer, LodgingSerializer

        user = self.request.user

        if item_type == "location":
            try:
                location = Location.objects.get(
                    Q(id=item_id) & (Q(user=user) | Q(is_public=True))
                )
                serializer = LocationSerializer(location, context={'request': self.request})
                return {"type": "location", **serializer.data}
            except Location.DoesNotExist:
                return {"error": f"Location {item_id} not found or not accessible"}

        elif item_type == "transportation":
            try:
                transportation = Transportation.objects.get(
                    Q(id=item_id) & (Q(user=user) | Q(is_public=True))
                )
                serializer = TransportationSerializer(transportation, context={'request': self.request})
                return {"type": "transportation", **serializer.data}
            except Transportation.DoesNotExist:
                return {"error": f"Transportation {item_id} not found or not accessible"}

        elif item_type == "lodging":
            try:
                lodging = Lodging.objects.get(
                    Q(id=item_id) & (Q(user=user) | Q(is_public=True))
                )
                serializer = LodgingSerializer(lodging, context={'request': self.request})
                return {"type": "lodging", **serializer.data}
            except Lodging.DoesNotExist:
                return {"error": f"Lodging {item_id} not found or not accessible"}

        else:
            return {"error": f"Invalid item_type: {item_type}. Must be 'location', 'transportation', or 'lodging'"}

    def list_items(
        self,
        item_type: str,
        limit: int = 20
    ) -> list:
        """
        List user's locations, transportations, or lodging.

        Args:
            item_type: Type of items to list. Options: "location", "transportation", "lodging"
            limit: Maximum number of results to return (default 20, max 50)

        Returns:
            List of items with basic info ordered by most recently updated
        """
        from adventures.models import Location, Transportation, Lodging

        user = self.request.user
        limit = min(limit, 50)
        results = []

        accessible = Q(user=user) | Q(is_public=True) | Q(collections__shared_with=user)

        if item_type == "location":
            items = Location.objects.filter(
                accessible
            ).distinct().order_by('-updated_at')[:limit]
            for item in items:
                results.append({
                    "type": "location",
                    "id": str(item.id),
                    "name": item.name,
                    "location": item.location,
                    "is_public": item.is_public,
                    "is_owner": item.user == user,
                    "updated_at": item.updated_at.isoformat(),
                })

        elif item_type == "transportation":
            items = Transportation.objects.filter(
                accessible
            ).distinct().order_by('-updated_at')[:limit]
            for item in items:
                results.append({
                    "type": "transportation",
                    "id": str(item.id),
                    "name": item.name,
                    "transportation_type": item.type,
                    "from_location": item.from_location,
                    "to_location": item.to_location,
                    "is_public": item.is_public,
                    "is_owner": item.user == user,
                    "updated_at": item.updated_at.isoformat(),
                })

        elif item_type == "lodging":
            items = Lodging.objects.filter(
                accessible
            ).distinct().order_by('-updated_at')[:limit]
            for item in items:
                results.append({
                    "type": "lodging",
                    "id": str(item.id),
                    "name": item.name,
                    "lodging_type": item.type,
                    "location": item.location,
                    "is_public": item.is_public,
                    "is_owner": item.user == user,
                    "updated_at": item.updated_at.isoformat(),
                })

        else:
            return [{"error": f"Invalid item_type: {item_type}. Must be 'location', 'transportation', or 'lodging'"}]

        return results

    # -------------------------------------------------------------------------
    # Create entities
    # -------------------------------------------------------------------------

    def create_location(
        self,
        name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        description: str = "",
        location: str = "",
        is_public: bool = True,
        tags: Optional[list] = None
    ) -> dict:
        """
        Create a new location.

        Args:
            name: Name of the location (required)
            latitude: Latitude coordinate (optional but recommended)
            longitude: Longitude coordinate (optional but recommended)
            description: Description of the location
            location: Address or place name
            is_public: Whether the location should be public (default False)
            tags: List of tags for categorization

        Returns:
            The created location details
        """
        from adventures.models import Location, Category
        from adventures.serializers import LocationSerializer

        user = self.request.user

        category, _ = Category.objects.get_or_create(
            user=user,
            name='general',
            defaults={'display_name': 'General', 'icon': ''}
        )

        location_obj = Location.objects.create(
            user=user,
            name=name,
            latitude=latitude,
            longitude=longitude,
            description=description,
            location=location,
            is_public=is_public,
            tags=tags or [],
            category=category
        )

        serializer = LocationSerializer(location_obj, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created location: {name}",
            "location": serializer.data
        }

    def create_transportation(
        self,
        name: str,
        type: str = "other",
        description: str = "",
        from_location: str = "",
        to_location: str = "",
        origin_latitude: Optional[float] = None,
        origin_longitude: Optional[float] = None,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
        flight_number: str = "",
        is_public: bool = True,
        tags: Optional[list] = None
    ) -> dict:
        """
        Create a new transportation.

        Args:
            name: Name of the transportation (required)
            type: Type of transportation. Options: "car", "plane", "train", "bus", "boat", "bike", "walking", "cab", "vtc", "other" (default "other")
            description: Description of the transportation
            from_location: Departure location name
            to_location: Arrival location name
            origin_latitude: Latitude of departure point
            origin_longitude: Longitude of departure point
            destination_latitude: Latitude of arrival point
            destination_longitude: Longitude of arrival point
            flight_number: Flight number (for air travel)
            is_public: Whether the transportation should be public (default False)
            tags: List of tags for categorization

        Returns:
            The created transportation details
        """
        from adventures.models import Transportation
        from adventures.serializers import TransportationSerializer

        user = self.request.user

        valid_types = ["car", "plane", "train", "bus", "boat", "bike", "walking", "cab", "vtc", "other"]
        if type not in valid_types:
            return {"error": f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}"}

        transportation = Transportation.objects.create(
            user=user,
            name=name,
            type=type,
            description=description or None,
            from_location=from_location or None,
            to_location=to_location or None,
            origin_latitude=origin_latitude,
            origin_longitude=origin_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            flight_number=flight_number or None,
            is_public=is_public,
            tags=tags or [],
        )

        serializer = TransportationSerializer(transportation, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created transportation: {name}",
            "transportation": serializer.data
        }

    def create_lodging(
        self,
        name: str,
        type: str = "other",
        description: str = "",
        location: str = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reservation_number: str = "",
        is_public: bool = True,
        tags: Optional[list] = None
    ) -> dict:
        """
        Create a new lodging.

        Args:
            name: Name of the lodging (required)
            type: Type of lodging. Options: "hotel", "hostel", "resort", "bnb", "campground", "cabin", "apartment", "house", "villa", "motel", "other" (default "other")
            description: Description of the lodging
            location: Address or place name
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            reservation_number: Reservation or confirmation number
            is_public: Whether the lodging should be public (default False)
            tags: List of tags for categorization

        Returns:
            The created lodging details
        """
        from adventures.models import Lodging
        from adventures.serializers import LodgingSerializer

        user = self.request.user

        valid_types = ["hotel", "hostel", "resort", "bnb", "campground", "cabin", "apartment", "house", "villa", "motel", "other"]
        if type not in valid_types:
            return {"error": f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}"}

        lodging = Lodging.objects.create(
            user=user,
            name=name,
            type=type,
            description=description or None,
            location=location or None,
            latitude=latitude,
            longitude=longitude,
            reservation_number=reservation_number or None,
            is_public=is_public,
            tags=tags or [],
        )

        serializer = LodgingSerializer(lodging, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created lodging: {name}",
            "lodging": serializer.data
        }

    # -------------------------------------------------------------------------
    # Edit entities (owner or collaborative on public)
    # -------------------------------------------------------------------------

    def edit_location(
        self,
        item_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        is_public: Optional[bool] = None,
        tags: Optional[list] = None
    ) -> dict:
        """
        Edit an existing location. Only the owner can edit.

        Args:
            item_id: UUID of the location to edit (required)
            name: New name for the location
            description: New description
            location: New address or place name
            latitude: New latitude coordinate
            longitude: New longitude coordinate
            is_public: Whether the location should be public
            tags: New list of tags

        Returns:
            The updated location details
        """
        from adventures.models import Location
        from adventures.serializers import LocationSerializer

        user = self.request.user

        try:
            loc = _get_editable_item(Location, item_id, user)
        except Location.DoesNotExist:
            return {"error": f"Location {item_id} not found or you don't have permission to edit it"}

        fields = {
            'name': name, 'description': description, 'location': location,
            'latitude': latitude, 'longitude': longitude, 'is_public': is_public,
            'tags': tags,
        }
        for field, value in fields.items():
            if value is not None:
                setattr(loc, field, value)
        loc.save()

        serializer = LocationSerializer(loc, context={'request': self.request})
        return {
            "success": True,
            "message": f"Updated location: {loc.name}",
            "location": serializer.data
        }

    def edit_transportation(
        self,
        item_id: str,
        name: Optional[str] = None,
        type: Optional[str] = None,
        description: Optional[str] = None,
        from_location: Optional[str] = None,
        to_location: Optional[str] = None,
        origin_latitude: Optional[float] = None,
        origin_longitude: Optional[float] = None,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
        flight_number: Optional[str] = None,
        is_public: Optional[bool] = None,
        tags: Optional[list] = None
    ) -> dict:
        """
        Edit an existing transportation. Only the owner can edit.

        Args:
            item_id: UUID of the transportation to edit (required)
            name: New name
            type: New type. Options: "car", "plane", "train", "bus", "boat", "bike", "walking", "cab", "vtc", "other"
            description: New description
            from_location: New departure location name
            to_location: New arrival location name
            origin_latitude: New latitude of departure point
            origin_longitude: New longitude of departure point
            destination_latitude: New latitude of arrival point
            destination_longitude: New longitude of arrival point
            flight_number: New flight number
            is_public: Whether the transportation should be public
            tags: New list of tags

        Returns:
            The updated transportation details
        """
        from adventures.models import Transportation
        from adventures.serializers import TransportationSerializer

        user = self.request.user

        try:
            transport = _get_editable_item(Transportation, item_id, user)
        except Transportation.DoesNotExist:
            return {"error": f"Transportation {item_id} not found or you don't have permission to edit it"}

        if type is not None:
            valid_types = ["car", "plane", "train", "bus", "boat", "bike", "walking", "cab", "vtc", "other"]
            if type not in valid_types:
                return {"error": f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}"}

        fields = {
            'name': name, 'type': type, 'description': description,
            'from_location': from_location, 'to_location': to_location,
            'origin_latitude': origin_latitude, 'origin_longitude': origin_longitude,
            'destination_latitude': destination_latitude, 'destination_longitude': destination_longitude,
            'flight_number': flight_number, 'is_public': is_public, 'tags': tags,
        }
        for field, value in fields.items():
            if value is not None:
                setattr(transport, field, value)
        transport.save()

        serializer = TransportationSerializer(transport, context={'request': self.request})
        return {
            "success": True,
            "message": f"Updated transportation: {transport.name}",
            "transportation": serializer.data
        }

    def edit_lodging(
        self,
        item_id: str,
        name: Optional[str] = None,
        type: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        reservation_number: Optional[str] = None,
        is_public: Optional[bool] = None,
        tags: Optional[list] = None
    ) -> dict:
        """
        Edit an existing lodging. Only the owner can edit.

        Args:
            item_id: UUID of the lodging to edit (required)
            name: New name
            type: New type. Options: "hotel", "hostel", "resort", "bnb", "campground", "cabin", "apartment", "house", "villa", "motel", "other"
            description: New description
            location: New address or place name
            latitude: New latitude coordinate
            longitude: New longitude coordinate
            reservation_number: New reservation number
            is_public: Whether the lodging should be public
            tags: New list of tags

        Returns:
            The updated lodging details
        """
        from adventures.models import Lodging
        from adventures.serializers import LodgingSerializer

        user = self.request.user

        try:
            lodging = _get_editable_item(Lodging, item_id, user)
        except Lodging.DoesNotExist:
            return {"error": f"Lodging {item_id} not found or you don't have permission to edit it"}

        if type is not None:
            valid_types = ["hotel", "hostel", "resort", "bnb", "campground", "cabin", "apartment", "house", "villa", "motel", "other"]
            if type not in valid_types:
                return {"error": f"Invalid type: {type}. Must be one of: {', '.join(valid_types)}"}

        fields = {
            'name': name, 'type': type, 'description': description,
            'location': location, 'latitude': latitude, 'longitude': longitude,
            'reservation_number': reservation_number, 'is_public': is_public, 'tags': tags,
        }
        for field, value in fields.items():
            if value is not None:
                setattr(lodging, field, value)
        lodging.save()

        serializer = LodgingSerializer(lodging, context={'request': self.request})
        return {
            "success": True,
            "message": f"Updated lodging: {lodging.name}",
            "lodging": serializer.data
        }

    # -------------------------------------------------------------------------
    # Visits
    # -------------------------------------------------------------------------

    def create_visit(
        self,
        item_type: str,
        item_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: str = "",
        rating: Optional[float] = None,
        total_price: Optional[float] = None,
        total_price_currency: str = "USD",
        number_of_people: Optional[int] = None
    ) -> dict:
        """
        Record a visit to a location, transportation, or lodging.

        Args:
            item_type: Type of item. Options: "location", "transportation", or "lodging"
            item_id: UUID of the item to add a visit to
            start_date: Start date in ISO format (YYYY-MM-DDTHH:MM:SS) or None for undated
            end_date: End date in ISO format (YYYY-MM-DDTHH:MM:SS) or None for undated
            notes: Notes about the visit
            rating: Rating from 0-5 (optional)
            total_price: Total price for this visit (optional)
            total_price_currency: Currency code, e.g. "USD", "EUR", "GBP" (default "USD")
            number_of_people: Number of people this price covers (optional)

        Returns:
            The created visit details including any linked activities
        """
        from adventures.models import Location, Transportation, Lodging, Visit
        from adventures.serializers import VisitSerializer
        from django.utils.dateparse import parse_datetime

        user = self.request.user

        parsed_start = parse_datetime(start_date) if start_date else None
        parsed_end = parse_datetime(end_date) if end_date else None

        if rating is not None and (rating < 0 or rating > 5):
            return {"error": "Rating must be between 0 and 5"}

        parent_kwargs = {}
        accessible = Q(user=user) | Q(collections__shared_with=user) | Q(is_public=True)

        if item_type == "location":
            try:
                parent = Location.objects.get(Q(id=item_id) & accessible)
                parent_kwargs['location'] = parent
            except Location.DoesNotExist:
                return {"error": f"Location {item_id} not found or not accessible"}

        elif item_type == "transportation":
            try:
                parent = Transportation.objects.get(Q(id=item_id) & accessible)
                parent_kwargs['transportation'] = parent
            except Transportation.DoesNotExist:
                return {"error": f"Transportation {item_id} not found or not accessible"}

        elif item_type == "lodging":
            try:
                parent = Lodging.objects.get(Q(id=item_id) & accessible)
                parent_kwargs['lodging'] = parent
            except Lodging.DoesNotExist:
                return {"error": f"Lodging {item_id} not found or not accessible"}
        else:
            return {"error": f"Invalid item_type: {item_type}"}

        price_kwargs = {}
        if total_price is not None:
            price_kwargs['total_price'] = total_price
            price_kwargs['total_price_currency'] = total_price_currency
        if number_of_people is not None:
            price_kwargs['number_of_people'] = number_of_people

        visit = Visit.objects.create(
            user=user,
            start_date=parsed_start,
            end_date=parsed_end,
            notes=notes,
            rating=rating,
            **parent_kwargs,
            **price_kwargs
        )

        serializer = VisitSerializer(visit, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created visit to {parent.name}",
            "visit": serializer.data
        }

    def edit_visit(
        self,
        visit_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: Optional[str] = None,
        rating: Optional[float] = None,
        total_price: Optional[float] = None,
        total_price_currency: Optional[str] = None,
        number_of_people: Optional[int] = None
    ) -> dict:
        """
        Edit an existing visit. Only the creator can edit.

        Args:
            visit_id: UUID of the visit to edit (required)
            start_date: New start date in ISO format (YYYY-MM-DDTHH:MM:SS)
            end_date: New end date in ISO format (YYYY-MM-DDTHH:MM:SS)
            notes: New notes
            rating: New rating from 0-5
            total_price: New total price for this visit
            total_price_currency: Currency code, e.g. "USD", "EUR", "GBP"
            number_of_people: Number of people this price covers

        Returns:
            The updated visit details including any linked activities
        """
        from adventures.models import Visit
        from adventures.serializers import VisitSerializer
        from django.utils.dateparse import parse_datetime

        user = self.request.user

        try:
            visit = Visit.objects.get(id=visit_id, user=user)
        except Visit.DoesNotExist:
            return {"error": f"Visit {visit_id} not found or you don't have permission to edit it"}

        if rating is not None and (rating < 0 or rating > 5):
            return {"error": "Rating must be between 0 and 5"}

        if start_date is not None:
            parsed = parse_datetime(start_date)
            if not parsed:
                return {"error": f"Invalid start_date format: {start_date}. Use YYYY-MM-DDTHH:MM:SS."}
            visit.start_date = parsed

        if end_date is not None:
            parsed = parse_datetime(end_date)
            if not parsed:
                return {"error": f"Invalid end_date format: {end_date}. Use YYYY-MM-DDTHH:MM:SS."}
            visit.end_date = parsed

        if notes is not None:
            visit.notes = notes
        if rating is not None:
            visit.rating = rating
        if total_price is not None:
            visit.total_price = total_price
            if total_price_currency:
                visit.total_price_currency = total_price_currency
        if number_of_people is not None:
            visit.number_of_people = number_of_people
        visit.save()

        serializer = VisitSerializer(visit, context={'request': self.request})
        return {
            "success": True,
            "message": f"Updated visit {visit_id}",
            "visit": serializer.data
        }

    def delete_visit(self, visit_id: str) -> dict:
        """
        Delete a visit. Only the creator can delete.

        Args:
            visit_id: UUID of the visit to delete (required)

        Returns:
            Success message or error
        """
        from adventures.models import Visit

        user = self.request.user

        try:
            visit = Visit.objects.get(id=visit_id, user=user)
        except Visit.DoesNotExist:
            return {"error": f"Visit {visit_id} not found or you don't have permission to delete it"}

        visit.delete()
        return {"success": True, "message": f"Deleted visit {visit_id}"}

    def list_visits(
        self,
        item_type: Optional[str] = None,
        item_id: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """
        List user's visits, optionally filtered by parent item.

        Args:
            item_type: Filter by parent type. Options: "location", "transportation", "lodging" (optional)
            item_id: Filter by parent item UUID (requires item_type)
            limit: Maximum number of results to return (default 20, max 50)

        Returns:
            List of visits with basic info ordered by most recent first
        """
        from adventures.models import Visit

        user = self.request.user
        limit = min(limit, 50)

        queryset = Visit.objects.filter(user=user)

        if item_type and item_id:
            if item_type == "location":
                queryset = queryset.filter(location_id=item_id)
            elif item_type == "transportation":
                queryset = queryset.filter(transportation_id=item_id)
            elif item_type == "lodging":
                queryset = queryset.filter(lodging_id=item_id)
            else:
                return [{"error": f"Invalid item_type: {item_type}"}]

        visits = queryset.order_by('-start_date', '-created_at')[:limit]

        results = []
        for v in visits:
            parent_name = None
            parent_type = None
            if v.location:
                parent_name = v.location.name
                parent_type = "location"
            elif v.transportation:
                parent_name = v.transportation.name
                parent_type = "transportation"
            elif v.lodging:
                parent_name = v.lodging.name
                parent_type = "lodging"

            results.append({
                "id": str(v.id),
                "parent_type": parent_type,
                "parent_name": parent_name,
                "start_date": v.start_date.isoformat() if v.start_date else None,
                "end_date": v.end_date.isoformat() if v.end_date else None,
                "notes": (v.notes or "")[:200],
                "rating": v.rating,
                "total_price": float(v.total_price.amount) if v.total_price else None,
                "total_price_currency": str(v.total_price_currency) if v.total_price else None,
                "number_of_people": v.number_of_people,
                "activity_count": v.activities.count(),
            })

        return results

    # -------------------------------------------------------------------------
    # Activities
    # -------------------------------------------------------------------------

    def create_activity(
        self,
        visit_id: str,
        name: str,
        sport_type: str = "General",
        distance: Optional[float] = None,
        elevation_gain: Optional[float] = None,
        elevation_loss: Optional[float] = None,
        moving_time: Optional[str] = None,
        start_date: Optional[str] = None,
        calories: Optional[float] = None,
        description: Optional[str] = None
    ) -> dict:
        """
        Add an activity to a visit (without GPX file upload).

        Args:
            visit_id: UUID of the visit to add the activity to (required)
            name: Name of the activity (required)
            sport_type: Type of sport (default "General"). Common: "Run", "Hike", "Ride", "Walk", "Swim"
            distance: Distance in meters (optional)
            elevation_gain: Elevation gain in meters (optional)
            elevation_loss: Elevation loss in meters (optional)
            moving_time: Moving time as HH:MM:SS string (optional)
            start_date: Start date in ISO format (YYYY-MM-DDTHH:MM:SS) (optional)
            calories: Calories burned (optional)
            description: Description/notes for the activity (optional)

        Returns:
            The created activity details
        """
        from adventures.models import Visit, Activity
        from adventures.serializers import ActivitySerializer
        from django.utils.dateparse import parse_datetime, parse_duration

        user = self.request.user

        try:
            visit = Visit.objects.get(id=visit_id, user=user)
        except Visit.DoesNotExist:
            return {"error": f"Visit {visit_id} not found or you don't have permission"}

        kwargs = {
            'user': user,
            'visit': visit,
            'name': name,
            'sport_type': sport_type,
        }

        if distance is not None:
            kwargs['distance'] = distance
        if elevation_gain is not None:
            kwargs['elevation_gain'] = elevation_gain
        if elevation_loss is not None:
            kwargs['elevation_loss'] = elevation_loss
        if moving_time is not None:
            parsed = parse_duration(moving_time)
            if not parsed:
                return {"error": f"Invalid moving_time format: {moving_time}. Use HH:MM:SS."}
            kwargs['moving_time'] = parsed
        if start_date is not None:
            parsed = parse_datetime(start_date)
            if not parsed:
                return {"error": f"Invalid start_date format: {start_date}. Use YYYY-MM-DDTHH:MM:SS."}
            kwargs['start_date'] = parsed
        if calories is not None:
            kwargs['calories'] = calories

        activity = Activity.objects.create(**kwargs)

        serializer = ActivitySerializer(activity, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created activity: {name}",
            "activity": serializer.data
        }

    # -------------------------------------------------------------------------
    # Collections
    # -------------------------------------------------------------------------

    def create_collection(
        self,
        name: str,
        description: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_public: bool = True
    ) -> dict:
        """
        Create a new trip collection.

        Args:
            name: Name of the collection (required)
            description: Description of the collection
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)
            is_public: Whether the collection should be public (default False)

        Returns:
            The created collection details
        """
        from adventures.models import Collection
        from adventures.serializers import CollectionSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user

        parsed_start = parse_date(start_date) if start_date else None
        parsed_end = parse_date(end_date) if end_date else None

        if start_date and not parsed_start:
            return {"error": f"Invalid start_date format: {start_date}. Use YYYY-MM-DD."}
        if end_date and not parsed_end:
            return {"error": f"Invalid end_date format: {end_date}. Use YYYY-MM-DD."}

        collection = Collection.objects.create(
            user=user,
            name=name,
            description=description or None,
            start_date=parsed_start,
            end_date=parsed_end,
            is_public=is_public,
        )

        serializer = CollectionSerializer(collection, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created collection: {name}",
            "collection": serializer.data
        }

    def edit_collection(
        self,
        collection_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> dict:
        """
        Edit an existing collection. Only the owner can edit.

        Args:
            collection_id: UUID of the collection to edit (required)
            name: New name for the collection
            description: New description
            start_date: New start date in YYYY-MM-DD format
            end_date: New end date in YYYY-MM-DD format
            is_public: Whether the collection should be public

        Returns:
            The updated collection details
        """
        from adventures.models import Collection
        from adventures.serializers import CollectionSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user

        try:
            collection = Collection.objects.get(id=collection_id, user=user)
        except Collection.DoesNotExist:
            return {"error": f"Collection {collection_id} not found or you don't have permission to edit it"}

        if start_date is not None:
            parsed = parse_date(start_date)
            if not parsed:
                return {"error": f"Invalid start_date format: {start_date}. Use YYYY-MM-DD."}
            collection.start_date = parsed

        if end_date is not None:
            parsed = parse_date(end_date)
            if not parsed:
                return {"error": f"Invalid end_date format: {end_date}. Use YYYY-MM-DD."}
            collection.end_date = parsed

        fields = {'name': name, 'description': description, 'is_public': is_public}
        for field, value in fields.items():
            if value is not None:
                setattr(collection, field, value)
        collection.save()

        serializer = CollectionSerializer(collection, context={'request': self.request})
        return {
            "success": True,
            "message": f"Updated collection: {collection.name}",
            "collection": serializer.data
        }

    def list_collections(self, status: str = "all", limit: int = 20) -> list:
        """
        List user's trip collections.

        Args:
            status: Filter by status. Options: "all", "upcoming", "in_progress", "completed", "folder"
            limit: Maximum number of collections to return (default 20, max 50)

        Returns:
            List of collections with basic info
        """
        from adventures.models import Collection
        from datetime import date

        user = self.request.user
        limit = min(limit, 50)
        today = date.today()

        queryset = Collection.objects.filter(user=user, is_archived=False)

        if status == "folder":
            queryset = queryset.filter(Q(start_date__isnull=True) | Q(end_date__isnull=True))
        elif status == "upcoming":
            queryset = queryset.filter(start_date__gt=today)
        elif status == "in_progress":
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
        elif status == "completed":
            queryset = queryset.filter(end_date__lt=today)

        collections = queryset.order_by('-updated_at')[:limit]

        results = []
        for c in collections:
            results.append({
                "id": str(c.id),
                "name": c.name,
                "description": (c.description or "")[:200],
                "is_public": c.is_public,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "location_count": c.locations.count(),
                "is_archived": c.is_archived,
            })

        return results

    def get_collection(self, collection_id: str) -> dict:
        """
        Get full details of a collection including its items and itinerary.

        Args:
            collection_id: UUID of the collection (required)

        Returns:
            Full collection details with locations, transportations, lodging, notes, checklists
        """
        from adventures.models import Collection
        from adventures.serializers import CollectionSerializer

        user = self.request.user

        try:
            collection = Collection.objects.get(
                Q(id=collection_id) & (Q(user=user) | Q(shared_with=user) | Q(is_public=True))
            )
        except Collection.DoesNotExist:
            return {"error": f"Collection {collection_id} not found or not accessible"}

        serializer = CollectionSerializer(collection, context={'request': self.request})
        return {"type": "collection", **serializer.data}

    def add_to_collection(
        self,
        item_type: str,
        item_id: str,
        collection_id: str
    ) -> dict:
        """
        Add a location, transportation, or lodging to a collection.

        Args:
            item_type: Type of item. Options: "location", "transportation", or "lodging"
            item_id: UUID of the item to add
            collection_id: UUID of the collection to add the item to

        Returns:
            Success message or error
        """
        from adventures.models import Location, Transportation, Lodging, Collection

        user = self.request.user

        try:
            collection = Collection.objects.get(
                Q(id=collection_id) & (Q(user=user) | Q(shared_with=user))
            )
        except Collection.DoesNotExist:
            return {"error": f"Collection {collection_id} not found or not accessible"}

        accessible = Q(user=user) | Q(collections__shared_with=user) | Q(is_public=True)

        if item_type == "location":
            try:
                location = Location.objects.get(Q(id=item_id) & accessible)
                location.collections.add(collection)
                return {"success": True, "message": f"Added location '{location.name}' to collection '{collection.name}'"}
            except Location.DoesNotExist:
                return {"error": f"Location {item_id} not found or not accessible"}

        elif item_type == "transportation":
            try:
                transportation = Transportation.objects.get(Q(id=item_id) & accessible)
                transportation.collections.add(collection)
                return {"success": True, "message": f"Added transportation '{transportation.name}' to collection '{collection.name}'"}
            except Transportation.DoesNotExist:
                return {"error": f"Transportation {item_id} not found or not accessible"}

        elif item_type == "lodging":
            try:
                lodging = Lodging.objects.get(Q(id=item_id) & accessible)
                lodging.collections.add(collection)
                return {"success": True, "message": f"Added lodging '{lodging.name}' to collection '{collection.name}'"}
            except Lodging.DoesNotExist:
                return {"error": f"Lodging {item_id} not found or not accessible"}

        else:
            return {"error": f"Invalid item_type: {item_type}. Must be 'location', 'transportation', or 'lodging'"}

    # -------------------------------------------------------------------------
    # Collection sharing
    # -------------------------------------------------------------------------

    def share_collection(self, collection_id: str, user_id: str) -> dict:
        """
        Share a collection with another user by sending an invite.

        Args:
            collection_id: UUID of the collection to share (required)
            user_id: UUID of the user to share with (required)

        Returns:
            Success message or error
        """
        from adventures.models import Collection, CollectionInvite
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = self.request.user

        try:
            collection = Collection.objects.get(id=collection_id, user=user)
        except Collection.DoesNotExist:
            return {"error": f"Collection {collection_id} not found or you are not the owner"}

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {"error": f"User {user_id} not found"}

        if target_user == user:
            return {"error": "Cannot share a collection with yourself"}

        if collection.shared_with.filter(id=target_user.id).exists():
            return {"error": f"Collection is already shared with {target_user.username}"}

        _, created = CollectionInvite.objects.get_or_create(
            collection=collection,
            invited_user=target_user,
        )

        if not created:
            return {"error": f"Invite already pending for {target_user.username}"}

        return {
            "success": True,
            "message": f"Sent invite to {target_user.username} for collection '{collection.name}'"
        }

    def unshare_collection(self, collection_id: str, user_id: str) -> dict:
        """
        Remove a user from a shared collection.

        Args:
            collection_id: UUID of the collection (required)
            user_id: UUID of the user to remove (required)

        Returns:
            Success message or error
        """
        from adventures.models import Collection
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user = self.request.user

        try:
            collection = Collection.objects.get(id=collection_id, user=user)
        except Collection.DoesNotExist:
            return {"error": f"Collection {collection_id} not found or you are not the owner"}

        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return {"error": f"User {user_id} not found"}

        if not collection.shared_with.filter(id=target_user.id).exists():
            return {"error": f"Collection is not shared with {target_user.username}"}

        collection.shared_with.remove(target_user)
        return {
            "success": True,
            "message": f"Removed {target_user.username} from collection '{collection.name}'"
        }

    # -------------------------------------------------------------------------
    # Notes
    # -------------------------------------------------------------------------

    def create_note(
        self,
        name: str,
        content: str = "",
        collection_id: Optional[str] = None,
        date: Optional[str] = None,
        links: Optional[list] = None,
        is_public: bool = True
    ) -> dict:
        """
        Create a new note, optionally linked to a collection.

        Args:
            name: Name/title of the note (required)
            content: Note content text
            collection_id: UUID of collection to attach the note to (optional)
            date: Date in YYYY-MM-DD format (optional)
            links: List of URLs to attach (optional)
            is_public: Whether the note should be public (default False)

        Returns:
            The created note details
        """
        from adventures.models import Note, Collection
        from adventures.serializers import NoteSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user
        kwargs = {'user': user, 'name': name, 'content': content or None, 'is_public': is_public}

        if collection_id:
            try:
                collection = Collection.objects.get(
                    Q(id=collection_id) & (Q(user=user) | Q(shared_with=user))
                )
                kwargs['collection'] = collection
            except Collection.DoesNotExist:
                return {"error": f"Collection {collection_id} not found or not accessible"}

        if date:
            parsed = parse_date(date)
            if not parsed:
                return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}
            kwargs['date'] = parsed

        if links:
            kwargs['links'] = links

        note = Note.objects.create(**kwargs)
        serializer = NoteSerializer(note, context={'request': self.request})
        return {"success": True, "message": f"Created note: {name}", "note": serializer.data}

    def edit_note(
        self,
        note_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        date: Optional[str] = None,
        links: Optional[list] = None,
        is_public: Optional[bool] = None
    ) -> dict:
        """
        Edit an existing note.

        Args:
            note_id: UUID of the note to edit (required)
            name: New name/title
            content: New content text
            date: New date in YYYY-MM-DD format
            links: New list of URLs
            is_public: Whether the note should be public

        Returns:
            The updated note details
        """
        from adventures.models import Note
        from adventures.serializers import NoteSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user

        try:
            note = Note.objects.get(id=note_id, user=user)
        except Note.DoesNotExist:
            return {"error": f"Note {note_id} not found or you don't have permission to edit it"}

        if date is not None:
            parsed = parse_date(date)
            if not parsed:
                return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}
            note.date = parsed

        fields = {'name': name, 'content': content, 'is_public': is_public, 'links': links}
        for field, value in fields.items():
            if value is not None:
                setattr(note, field, value)
        note.save()

        serializer = NoteSerializer(note, context={'request': self.request})
        return {"success": True, "message": f"Updated note: {note.name}", "note": serializer.data}

    def delete_note(self, note_id: str) -> dict:
        """
        Delete a note. Only the creator can delete.

        Args:
            note_id: UUID of the note to delete (required)

        Returns:
            Success message or error
        """
        from adventures.models import Note

        user = self.request.user
        try:
            note = Note.objects.get(id=note_id, user=user)
        except Note.DoesNotExist:
            return {"error": f"Note {note_id} not found or you don't have permission to delete it"}

        note.delete()
        return {"success": True, "message": f"Deleted note {note_id}"}

    def list_notes(
        self,
        collection_id: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """
        List notes, optionally filtered by collection.

        Args:
            collection_id: Filter by collection UUID (optional)
            limit: Maximum number of results (default 20, max 50)

        Returns:
            List of notes with basic info
        """
        from adventures.models import Note

        user = self.request.user
        limit = min(limit, 50)

        queryset = Note.objects.filter(user=user)
        if collection_id:
            queryset = queryset.filter(collection_id=collection_id)

        notes = queryset.order_by('-updated_at')[:limit]

        return [{
            "id": str(n.id),
            "name": n.name,
            "content": (n.content or "")[:200],
            "date": n.date.isoformat() if n.date else None,
            "collection_id": str(n.collection_id) if n.collection_id else None,
            "is_public": n.is_public,
        } for n in notes]

    # -------------------------------------------------------------------------
    # Checklists
    # -------------------------------------------------------------------------

    def create_checklist(
        self,
        name: str,
        items: Optional[list] = None,
        collection_id: Optional[str] = None,
        date: Optional[str] = None,
        is_public: bool = True
    ) -> dict:
        """
        Create a new checklist with optional items.

        Args:
            name: Name of the checklist (required)
            items: List of item names (strings) to add to the checklist (optional)
            collection_id: UUID of collection to attach the checklist to (optional)
            date: Date in YYYY-MM-DD format (optional)
            is_public: Whether the checklist should be public (default False)

        Returns:
            The created checklist details with items
        """
        from adventures.models import Checklist, ChecklistItem, Collection
        from adventures.serializers import ChecklistSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user
        kwargs = {'user': user, 'name': name, 'is_public': is_public}

        if collection_id:
            try:
                collection = Collection.objects.get(
                    Q(id=collection_id) & (Q(user=user) | Q(shared_with=user))
                )
                kwargs['collection'] = collection
            except Collection.DoesNotExist:
                return {"error": f"Collection {collection_id} not found or not accessible"}

        if date:
            parsed = parse_date(date)
            if not parsed:
                return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}
            kwargs['date'] = parsed

        checklist = Checklist.objects.create(**kwargs)

        if items:
            for item_name in items:
                ChecklistItem.objects.create(
                    user=user,
                    checklist=checklist,
                    name=item_name,
                )

        serializer = ChecklistSerializer(checklist, context={'request': self.request})
        return {"success": True, "message": f"Created checklist: {name}", "checklist": serializer.data}

    def edit_checklist(
        self,
        checklist_id: str,
        name: Optional[str] = None,
        date: Optional[str] = None,
        is_public: Optional[bool] = None,
        add_items: Optional[list] = None,
        check_items: Optional[list] = None,
        uncheck_items: Optional[list] = None,
        remove_items: Optional[list] = None
    ) -> dict:
        """
        Edit a checklist: rename, add/remove/check items.

        Args:
            checklist_id: UUID of the checklist to edit (required)
            name: New name for the checklist
            date: New date in YYYY-MM-DD format
            is_public: Whether the checklist should be public
            add_items: List of new item names (strings) to add
            check_items: List of item UUIDs to mark as checked
            uncheck_items: List of item UUIDs to mark as unchecked
            remove_items: List of item UUIDs to remove

        Returns:
            The updated checklist details with items
        """
        from adventures.models import Checklist, ChecklistItem
        from adventures.serializers import ChecklistSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user

        try:
            checklist = Checklist.objects.get(id=checklist_id, user=user)
        except Checklist.DoesNotExist:
            return {"error": f"Checklist {checklist_id} not found or you don't have permission to edit it"}

        if date is not None:
            parsed = parse_date(date)
            if not parsed:
                return {"error": f"Invalid date format: {date}. Use YYYY-MM-DD."}
            checklist.date = parsed

        if name is not None:
            checklist.name = name
        if is_public is not None:
            checklist.is_public = is_public
        checklist.save()

        if add_items:
            for item_name in add_items:
                ChecklistItem.objects.create(user=user, checklist=checklist, name=item_name)

        if check_items:
            ChecklistItem.objects.filter(id__in=check_items, checklist=checklist).update(is_checked=True)

        if uncheck_items:
            ChecklistItem.objects.filter(id__in=uncheck_items, checklist=checklist).update(is_checked=False)

        if remove_items:
            ChecklistItem.objects.filter(id__in=remove_items, checklist=checklist).delete()

        checklist.refresh_from_db()
        serializer = ChecklistSerializer(checklist, context={'request': self.request})
        return {"success": True, "message": f"Updated checklist: {checklist.name}", "checklist": serializer.data}

    def delete_checklist(self, checklist_id: str) -> dict:
        """
        Delete a checklist and all its items. Only the creator can delete.

        Args:
            checklist_id: UUID of the checklist to delete (required)

        Returns:
            Success message or error
        """
        from adventures.models import Checklist

        user = self.request.user
        try:
            checklist = Checklist.objects.get(id=checklist_id, user=user)
        except Checklist.DoesNotExist:
            return {"error": f"Checklist {checklist_id} not found or you don't have permission to delete it"}

        checklist.delete()
        return {"success": True, "message": f"Deleted checklist {checklist_id}"}

    def list_checklists(
        self,
        collection_id: Optional[str] = None,
        limit: int = 20
    ) -> list:
        """
        List checklists, optionally filtered by collection.

        Args:
            collection_id: Filter by collection UUID (optional)
            limit: Maximum number of results (default 20, max 50)

        Returns:
            List of checklists with item counts
        """
        from adventures.models import Checklist

        user = self.request.user
        limit = min(limit, 50)

        queryset = Checklist.objects.filter(user=user)
        if collection_id:
            queryset = queryset.filter(collection_id=collection_id)

        checklists = queryset.order_by('-updated_at')[:limit]

        return [{
            "id": str(c.id),
            "name": c.name,
            "date": c.date.isoformat() if c.date else None,
            "collection_id": str(c.collection_id) if c.collection_id else None,
            "is_public": c.is_public,
            "total_items": c.checklistitem_set.count(),
            "checked_items": c.checklistitem_set.filter(is_checked=True).count(),
        } for c in checklists]

    # -------------------------------------------------------------------------
    # Templates
    # -------------------------------------------------------------------------

    def list_templates(self, limit: int = 20) -> list:
        """
        List available collection templates (own + public).

        Args:
            limit: Maximum number of results (default 20, max 50)

        Returns:
            List of templates with basic info
        """
        from adventures.models import CollectionTemplate

        user = self.request.user
        limit = min(limit, 50)

        templates = CollectionTemplate.objects.filter(
            Q(user=user) | Q(is_public=True)
        ).distinct().order_by('-updated_at')[:limit]

        return [{
            "id": str(t.id),
            "name": t.name,
            "description": (t.description or "")[:200],
            "is_public": t.is_public,
            "is_owner": t.user == user,
        } for t in templates]

    def apply_template(
        self,
        template_id: str,
        collection_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Create a new collection from a template.

        Args:
            template_id: UUID of the template to apply (required)
            collection_name: Name for the new collection (required)
            start_date: Start date in YYYY-MM-DD format (optional)
            end_date: End date in YYYY-MM-DD format (optional)

        Returns:
            The created collection details
        """
        from adventures.models import CollectionTemplate, Collection, Note, Checklist, ChecklistItem
        from adventures.serializers import CollectionSerializer
        from django.utils.dateparse import parse_date

        user = self.request.user

        try:
            template = CollectionTemplate.objects.get(
                Q(id=template_id) & (Q(user=user) | Q(is_public=True))
            )
        except CollectionTemplate.DoesNotExist:
            return {"error": f"Template {template_id} not found or not accessible"}

        parsed_start = parse_date(start_date) if start_date else None
        parsed_end = parse_date(end_date) if end_date else None

        collection = Collection.objects.create(
            user=user,
            name=collection_name,
            description=template.description,
            start_date=parsed_start,
            end_date=parsed_end,
        )

        data = template.template_data or {}

        # Create notes from template
        for note_data in data.get('notes', []):
            Note.objects.create(
                user=user,
                collection=collection,
                name=note_data.get('name', 'Untitled'),
                content=note_data.get('content', ''),
                links=note_data.get('links', []),
            )

        # Create checklists from template
        for cl_data in data.get('checklists', []):
            checklist = Checklist.objects.create(
                user=user,
                collection=collection,
                name=cl_data.get('name', 'Untitled'),
            )
            for item_data in cl_data.get('items', []):
                ChecklistItem.objects.create(
                    user=user,
                    checklist=checklist,
                    name=item_data.get('name', ''),
                    is_checked=False,
                )

        serializer = CollectionSerializer(collection, context={'request': self.request})
        return {
            "success": True,
            "message": f"Created collection '{collection_name}' from template '{template.name}'",
            "collection": serializer.data
        }

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> dict:
        """
        Get address information from coordinates using reverse geocoding.

        Args:
            latitude: Latitude coordinate (required)
            longitude: Longitude coordinate (required)

        Returns:
            Address details including display_name, country, region, city, etc.
        """
        from adventures.geocoding import reverse_geocode as do_reverse_geocode

        user = self.request.user
        result = do_reverse_geocode(latitude, longitude, user)
        return result

    def list_reference_types(self) -> dict:
        """
        List all available reference types (transportation types, lodging types, adventure types, activity types).

        Returns:
            Dictionary with transportation_types, lodging_types, adventure_types, and activity_types
        """
        from adventures.models import TRANSPORTATION_TYPES, LODGING_TYPES, AdventureType, ActivityType

        adventure_types = list(
            AdventureType.objects.filter(is_active=True)
            .order_by('display_order', 'name')
            .values('key', 'name', 'icon')
        )

        activity_types = list(
            ActivityType.objects.filter(is_active=True)
            .order_by('display_order', 'name')
            .values('key', 'name', 'icon', 'color')
        )

        return {
            "transportation_types": [{"key": k, "label": v} for k, v in TRANSPORTATION_TYPES],
            "lodging_types": [{"key": k, "label": v} for k, v in LODGING_TYPES],
            "adventure_types": adventure_types,
            "activity_types": activity_types,
        }
