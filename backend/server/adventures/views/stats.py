from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from adventures.services.dashboard import build_dashboard_data
from adventures.services.user_stats import UserStatsService
from django.contrib.auth import get_user_model

User = get_user_model()
_stats_service = UserStatsService()


class StatsViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing the stats of a user.
    """

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def dashboard(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'User is not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            events_days = int(request.query_params.get('events_days', 30))
        except (TypeError, ValueError):
            events_days = 30

        events_days = max(1, min(events_days, 90))

        data = build_dashboard_data(
            request.user,
            request.user,
            events_days=events_days,
            request=request,
        )
        return Response(data)

    @action(detail=False, methods=['get'], url_path=r'counts/(?P<username>[\w.@+-]+)')
    def counts(self, request, username):
        if request.user.username == username:
            user = get_object_or_404(User, username=username)
        else:
            user = get_object_or_404(User, username=username, public_profile=True)

        user.email = None

        return Response(_stats_service.build_user_stats(user, request.user, include_categories=True))
