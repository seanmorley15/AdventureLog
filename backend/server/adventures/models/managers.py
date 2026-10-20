from django.db import models
from django.db.models import Q

class LocationManager(models.Manager):
    def retrieve_locations(self, user, include_owned=False, include_shared=False, include_public=False):
        query = Q()

        if include_owned:
            query |= Q(user=user)

        if include_shared:
            query |= Q(collections__shared_with=user) | Q(collections__user=user)

        if include_public:
            query |= Q(is_public=True)

        return self.filter(query).distinct()
