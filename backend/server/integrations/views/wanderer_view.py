# views.py
import requests
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound

from integrations.models import WandererIntegration
from integrations.wanderer_services import get_valid_session, login_to_wanderer, IntegrationError
from django.utils import timezone

class WandererIntegrationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_obj(self):
        try:
            return WandererIntegration.objects.filter(user=self.request.user).first()
        except WandererIntegration.DoesNotExist:
            raise NotFound("Wanderer integration not found.")

    # def list(self, request):
    #     try:
    #         inst = self._get_obj()
    #     except NotFound:
    #         return Response([], status=status.HTTP_200_OK)
    #     return Response({
    #         "id": inst.id,
    #         "server_url": inst.server_url,
    #         "username": inst.username,
    #         "is_connected": bool(inst.token and inst.token_expiry and inst.token_expiry > timezone.now()),
    #         "token_expiry": inst.token_expiry,
    #     })

    def create(self, request):
        if WandererIntegration.objects.filter(user=request.user).exists():
            raise ValidationError("Wanderer integration already exists. Use UPDATE instead.")
        
        if not request.user.is_authenticated:
            raise ValidationError("You must be authenticated to create a Wanderer integration.")

        server_url = request.data.get("server_url")
        username = request.data.get("username")
        password = request.data.get("password")
        if not server_url or not username or not password:
            raise ValidationError(
                "Must provide server_url, username + password in request data."
            )

        inst = WandererIntegration(
            user=request.user,
            server_url=server_url.rstrip("/"),
            username=username,
        )

        try:
            token, expiry = login_to_wanderer(inst, password)
        except IntegrationError:
            raise ValidationError({"error": "Failed to authenticate with Wanderer server."})

        inst.token = token
        inst.token_expiry = expiry
        inst.save()

        return Response(
            {"message": "Wanderer integration created and authenticated successfully."},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        inst = self._get_obj()

        if not inst:
            raise NotFound("Wanderer integration not found.")
        if not self.request.user.is_authenticated:
            raise ValidationError("You must be authenticated to update the integration.")

        changed = False
        for field in ("server_url", "username"):
            if field in request.data and getattr(inst, field) != request.data[field]:
                setattr(inst, field, request.data[field].rstrip("/") if field=="server_url" else request.data[field])
                changed = True

        password = request.data.get("password")
        if not changed and not password:
            return Response(
                {"detail": "Nothing updated: send at least one of server_url, username, or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If password provided: re-auth / token renewal
        if password:
            try:
                token, expiry = login_to_wanderer(inst, password)
            except IntegrationError:
                raise ValidationError({"error": "Failed to update integration. Please check your credentials and try again."})
            inst.token = token
            inst.token_expiry = expiry

        inst.save()
        return Response({"message": "Integration updated successfully."})

    @action(detail=False, methods=["post"])
    def disable(self, request):
        inst = self._get_obj()

        if not inst:
            raise NotFound("Wanderer integration not found.")
        if not self.request.user.is_authenticated:
            raise ValidationError("You must be authenticated to disable the integration.")

        inst.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        inst = self._get_obj()

        if not self.request.user.is_authenticated:
            raise ValidationError("You must be authenticated to refresh the integration.")

        password = request.data.get("password")
        try:
            session = get_valid_session(inst, password_for_reauth=password)
        except IntegrationError:
            raise ValidationError({"detail": "An error occurred while refreshing the integration."})

        return Response({
            "token": inst.token,
            "token_expiry": inst.token_expiry,
            "is_connected": True,
        })

    @action(detail=False, methods=["get"], url_path='trails')
    def trails(self, request):
        inst = self._get_obj()

        if not self.request.user.is_authenticated:
            raise ValidationError("You must be authenticated to access trails.")
        
        # Check if we need to prompt for password
        password = request.query_params.get("password")  # Allow password via query param if needed
        
        try:
            session = get_valid_session(inst, password_for_reauth=password)
        except IntegrationError as e:
            # If session expired and no password provided, give a helpful error
            if "password is required" in str(e).lower():
                raise ValidationError({
                    "detail": "Session expired or not authenticated. Please provide your password to re-authenticate.",
                    "requires_password": True
                })
            raise ValidationError({"detail": "An error occurred while refreshing the integration."})

        # Pass along all query parameters except password
        params = {k: v for k, v in request.query_params.items() if k != "password"}
        
        url = f"{inst.server_url.rstrip('/')}/api/v1/trail"
        try:
            response = session.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            raise ValidationError({"detail": f"Error fetching trails"})

        return Response(response.json())