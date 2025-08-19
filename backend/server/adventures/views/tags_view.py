from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from adventures.models import Location

class ActivityTypesView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Retrieve a list of distinct activity types for locations associated with the current user.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: A response containing a list of distinct activity types.
        """
        types = Location.objects.filter(user=request.user).values_list('tags', flat=True).distinct()

        allTypes = []

        for i in types:
            if not i:
                continue
            for x in i:
                if x and x not in allTypes:
                    allTypes.append(x)

        return Response(allTypes)