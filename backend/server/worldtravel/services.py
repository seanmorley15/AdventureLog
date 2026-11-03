from .models import City, CityAlias, VisitedCity, VisitedRegion


def resolve_city(city_id):
    """
    The city with this id, or the one it was merged into when the dataset listed the same town twice.

    For ids that were saved before the merge, such as the ones in an old backup.
    """
    if not city_id:
        return None
    city = City.objects.filter(id=city_id).first()
    if city is not None:
        return city
    alias = CityAlias.objects.filter(old_id=city_id).select_related('city').first()
    return alias.city if alias else None


def _mark_visited(model, fk_name, user_id, ids, dry_run):
    ids = set(ids)
    if not ids:
        return set()

    # Neither visited model has a unique constraint (save() enforces it, and bulk_create
    # skips save()), so rows that already exist have to be filtered out here.
    existing = set(
        model.objects.filter(user_id=user_id, **{f'{fk_name}_id__in': ids})
        .values_list(f'{fk_name}_id', flat=True)
    )
    missing = ids - existing
    if missing and not dry_run:
        model.objects.bulk_create(
            [model(user_id=user_id, **{f'{fk_name}_id': pk}) for pk in missing]
        )
    return missing


def mark_regions_visited(user_id, region_ids, dry_run=False):
    """Mark regions visited for a user. Returns the ids that were not already visited."""
    return _mark_visited(VisitedRegion, 'region', user_id, region_ids, dry_run)


def mark_cities_visited(user_id, city_ids, dry_run=False):
    """Mark cities visited for a user. Returns the ids that were not already visited."""
    return _mark_visited(VisitedCity, 'city', user_id, city_ids, dry_run)
