"""The home screen summary. A user's public stats are served by the users app."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.serializers.calendar import DashboardSerializer
from adventures.services.dashboard import build_dashboard_data
from core.serializers import validated


class DashboardQuerySerializer(serializers.Serializer):
    events_days = serializers.IntegerField(
        default=30, min_value=1, max_value=90, help_text='How many days ahead `upcoming_events` looks.'
    )


class DashboardView(APIView):
    openapi_tags = ['Dashboard']

    @extend_schema(parameters=[DashboardQuerySerializer], responses=DashboardSerializer)
    def get(self, request):
        """
        Get the dashboard

        Your stats, recently changed places, upcoming and current trips, upcoming events, and
        how many invites are waiting.
        """
        params = validated(DashboardQuerySerializer, request.query_params)
        return Response(build_dashboard_data(request.user, request.user, events_days=params['events_days'], request=request))
