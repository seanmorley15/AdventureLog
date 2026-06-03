from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Q, QuerySet

from adventures.models import (
    Activity,
    Checklist,
    Collection,
    Location,
    Lodging,
    Note,
    Transportation,
)
from users.models import CustomUser as User
from worldtravel.models import City, Country, Region, VisitedCity, VisitedRegion


ALL_SEARCH_TYPES = frozenset(
    {
        'location',
        'collection',
        'lodging',
        'transportation',
        'note',
        'checklist',
        'activity',
        'country',
        'region',
        'city',
        'user',
    }
)

REFERENCE_TYPE_LIMIT = 10
ICONTAINS_SCORE = 0.45
PARTIAL_MATCH_SCORE = 0.35
LOCATION_SCORE_BOOST = 1.0

# Higher values sort first when merging mixed entity results.
TYPE_SORT_PRIORITY: dict[str, int] = {
    'location': 100,
    'collection': 40,
    'lodging': 20,
    'transportation': 20,
    'note': 20,
    'checklist': 20,
    'activity': 20,
    'country': 5,
    'region': 5,
    'city': 5,
    'user': 5,
}


class SearchValidationError(ValueError):
    pass


def _tokenize(term: str) -> list[str]:
    return [token for token in re.split(r'\s+', term.strip()) if len(token) >= 2]


def _safe_raw_token(token: str) -> str:
    cleaned = re.sub(r'[^\w\s-]', '', token, flags=re.UNICODE).strip()
    return cleaned.replace(' ', '')


def _icontains_filter(term: str, field_names: tuple[str, ...]) -> Q:
    filters = Q()
    if not term:
        return filters

    for field in field_names:
        filters |= Q(**{f'{field}__icontains': term})

    for token in _tokenize(term):
        for field in field_names:
            filters |= Q(**{f'{field}__icontains': token})

    return filters


def _fts_queries(term: str) -> tuple[SearchQuery, SearchQuery | None]:
    plain = SearchQuery(term, search_type='plain')
    raw_tokens = [_safe_raw_token(token) for token in _tokenize(term)]
    raw_tokens = [token for token in raw_tokens if len(token) >= 2]
    prefix = None
    if raw_tokens:
        prefix = SearchQuery(
            ' & '.join(f'{token}:*' for token in raw_tokens),
            search_type='raw',
        )
    return plain, prefix


def _apply_text_search(
    base_qs: QuerySet,
    vector: SearchVector,
    term: str,
    icontains_fields: tuple[str, ...],
) -> QuerySet:
    plain_query, prefix_query = _fts_queries(term)
    text_filter = Q(search=plain_query) | _icontains_filter(term, icontains_fields)
    if prefix_query is not None:
        text_filter |= Q(search=prefix_query)

    return (
        base_qs.annotate(search=vector, rank=SearchRank(vector, plain_query))
        .filter(text_filter)
        .distinct()
    )


def _location_subtitle_and_meta(location: Location) -> tuple[str, dict[str, Any]]:
    parts: list[str] = []
    meta: dict[str, Any] = {}

    if location.location:
        parts.append(location.location)

    if location.category_id:
        meta['category_icon'] = location.category.icon or '🌍'
        meta['category_name'] = location.category.display_name or location.category.name
        parts.append(meta['category_name'])

    if location.country_id and not parts:
        parts.append(location.country.name)

    return ' · '.join(parts), meta


def _sort_key(
    score: float,
    *,
    entity_type: str,
    recency: float = 0.0,
    label: str = '',
) -> tuple[int, float, float, str]:
    """Homogeneous sort key; locations and other types can be ranked together safely."""
    type_priority = TYPE_SORT_PRIORITY.get(entity_type, 0)
    adjusted_score = score + LOCATION_SCORE_BOOST if entity_type == 'location' else score
    return (type_priority, adjusted_score, recency, label.lower())


@dataclass
class SearchHit:
    type: str
    id: str
    title: str
    subtitle: str
    url: str
    score: float
    meta: dict[str, Any] = field(default_factory=dict)
    sort_key: tuple = field(default_factory=tuple, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            'type': self.type,
            'id': self.id,
            'title': self.title,
            'subtitle': self.subtitle,
            'url': self.url,
            'score': round(self.score, 4),
            'meta': self.meta,
        }


def normalize_query(query: str) -> str:
    normalized = query.strip()
    if len(normalized) < 2:
        raise SearchValidationError('Search query must be at least 2 characters')
    if len(normalized) > 100:
        normalized = normalized[:100]
    return normalized


def _search_vector(*field_names: str) -> SearchVector:
    return SearchVector(*field_names, config='english')


def _collection_subtitle(collection: Collection | None) -> str:
    if collection is None:
        return ''
    return collection.name


def _collection_url(collection_id) -> str:
    return f'/collections/{collection_id}'


def _search_locations(user: User, term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    vector = _search_vector('name', 'description', 'location')
    icontains_fields = ('name', 'description', 'location')
    base_qs = Location.objects.filter(user=user).select_related('country', 'category')
    matched = _apply_text_search(base_qs, vector, term, icontains_fields)
    qs = matched.order_by('-rank', '-updated_at')[:fetch_limit]
    total = matched.count()
    hits = []
    for location in qs:
        subtitle, meta = _location_subtitle_and_meta(location)
        score = float(location.rank or 0) or PARTIAL_MATCH_SCORE
        hits.append(
            SearchHit(
                type='location',
                id=str(location.id),
                title=location.name,
                subtitle=subtitle,
                url=f'/locations/{location.id}',
                score=score,
                meta=meta,
                sort_key=_sort_key(
                    score,
                    entity_type='location',
                    recency=location.updated_at.timestamp(),
                    label=location.name,
                ),
            )
        )
    return hits, total


def _search_collections(user: User, term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    vector = _search_vector('name', 'description')
    icontains_fields = ('name', 'description')
    base_qs = Collection.objects.filter(Q(user=user) | Q(shared_with=user)).distinct()
    matched = _apply_text_search(base_qs, vector, term, icontains_fields)
    qs = matched.order_by('-rank', '-updated_at')[:fetch_limit]
    total = matched.count()
    hits = []
    for collection in qs:
        is_shared = collection.user_id != user.id
        score = float(collection.rank or 0) or PARTIAL_MATCH_SCORE
        hits.append(
            SearchHit(
                type='collection',
                id=str(collection.id),
                title=collection.name,
                subtitle=collection.description or '',
                url=_collection_url(collection.id),
                score=score,
                meta={'is_shared': is_shared},
                sort_key=_sort_key(
                    score,
                    entity_type='collection',
                    recency=collection.updated_at.timestamp(),
                    label=collection.name,
                ),
            )
        )
    return hits, total


def _search_collection_entity(
    *,
    entity_type: str,
    model,
    user: User,
    term: str,
    vector_fields: tuple[str, ...],
    fetch_limit: int,
) -> tuple[list[SearchHit], int]:
    vector = _search_vector(*vector_fields)
    base_qs = model.objects.filter(user=user).select_related('collection')
    matched = _apply_text_search(base_qs, vector, term, vector_fields)
    qs = matched.order_by('-rank', '-updated_at')[:fetch_limit]
    total = matched.count()
    hits = []
    for obj in qs:
        collection = getattr(obj, 'collection', None)
        url = _collection_url(collection.id) if collection else '/collections'
        score = float(obj.rank or 0) or PARTIAL_MATCH_SCORE
        hits.append(
            SearchHit(
                type=entity_type,
                id=str(obj.id),
                title=obj.name,
                subtitle=_collection_subtitle(collection),
                url=url,
                score=score,
                meta={'collection_id': str(collection.id), 'collection_name': collection.name} if collection else {},
                sort_key=_sort_key(
                    score,
                    entity_type=entity_type,
                    recency=obj.updated_at.timestamp(),
                    label=obj.name,
                ),
            )
        )
    return hits, total


def _search_activities(user: User, term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    vector = _search_vector('name')
    icontains_fields = ('name',)
    base_qs = Activity.objects.filter(user=user).select_related('visit__location')
    matched = _apply_text_search(base_qs, vector, term, icontains_fields)
    qs = matched.order_by('-rank', '-start_date')[:fetch_limit]
    total = matched.count()
    hits = []
    for activity in qs:
        location = activity.visit.location if activity.visit_id else None
        url = f'/locations/{location.id}' if location else '/locations'
        subtitle = location.name if location else activity.sport_type
        score = float(activity.rank or 0) or PARTIAL_MATCH_SCORE
        hits.append(
            SearchHit(
                type='activity',
                id=str(activity.id),
                title=activity.name,
                subtitle=subtitle,
                url=url,
                score=score,
                meta={'location_id': str(location.id), 'location_name': location.name} if location else {},
                sort_key=_sort_key(
                    score,
                    entity_type='activity',
                    recency=activity.start_date.timestamp() if activity.start_date else 0,
                    label=activity.name,
                ),
            )
        )
    return hits, total


def _search_countries(term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    vector = _search_vector('name', 'country_code')
    icontains_fields = ('name', 'country_code')
    base_qs = Country.objects.all()
    matched = _apply_text_search(base_qs, vector, term, icontains_fields)
    qs = matched.order_by('-rank', 'name')[: min(fetch_limit, REFERENCE_TYPE_LIMIT)]
    total = matched.count()
    hits = []
    for country in qs:
        score = float(country.rank or 0) or PARTIAL_MATCH_SCORE
        hits.append(
            SearchHit(
                type='country',
                id=country.country_code,
                title=country.name,
                subtitle=country.country_code,
                url=f'/worldtravel/{country.country_code}',
                score=score,
                sort_key=_sort_key(score, entity_type='country', label=country.name),
            )
        )
    return hits, total


def _search_regions(user: User, term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    visited_region_ids = set(
        VisitedRegion.objects.filter(user=user).values_list('region_id', flat=True)
    )
    base_qs = Region.objects.filter(_icontains_filter(term, ('name',))).select_related('country')
    qs = base_qs.order_by('name')[: min(fetch_limit, REFERENCE_TYPE_LIMIT)]
    total = base_qs.count()
    hits = []
    for region in qs:
        country_code = region.country.country_code if region.country_id else region.id.split('-')[0]
        hits.append(
            SearchHit(
                type='region',
                id=region.id,
                title=region.name,
                subtitle=region.country.name if region.country_id else '',
                url=f'/worldtravel/{country_code}/{region.id}',
                score=ICONTAINS_SCORE,
                meta={'is_visited': region.id in visited_region_ids},
                sort_key=_sort_key(ICONTAINS_SCORE, entity_type='region', label=region.name),
            )
        )
    return hits, total


def _search_cities(user: User, term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    visited_city_ids = set(
        VisitedCity.objects.filter(user=user).values_list('city_id', flat=True)
    )
    base_qs = City.objects.filter(_icontains_filter(term, ('name',))).select_related('region__country')
    qs = base_qs.order_by('name')[: min(fetch_limit, REFERENCE_TYPE_LIMIT)]
    total = base_qs.count()
    hits = []
    for city in qs:
        country_code = city.region.country.country_code if city.region_id and city.region.country_id else ''
        hits.append(
            SearchHit(
                type='city',
                id=city.id,
                title=city.name,
                subtitle=f'{city.region.name}, {city.region.country.name}' if city.region_id else '',
                url=f'/worldtravel/{country_code}/{city.region_id}/{city.id}' if country_code else '/worldtravel',
                score=ICONTAINS_SCORE,
                meta={'is_visited': city.id in visited_city_ids},
                sort_key=_sort_key(ICONTAINS_SCORE, entity_type='city', label=city.name),
            )
        )
    return hits, total


def _search_users(term: str, fetch_limit: int) -> tuple[list[SearchHit], int]:
    base_qs = User.objects.filter(
        _icontains_filter(term, ('username', 'first_name', 'last_name'))
        & Q(public_profile=True)
    )
    qs = base_qs.order_by('username')[: min(fetch_limit, REFERENCE_TYPE_LIMIT)]
    total = base_qs.count()
    hits = []
    for profile_user in qs:
        display_name = profile_user.get_full_name() or profile_user.username
        hits.append(
            SearchHit(
                type='user',
                id=str(profile_user.uuid),
                title=display_name,
                subtitle=f'@{profile_user.username}',
                url=f'/profile/{profile_user.username}',
                score=ICONTAINS_SCORE,
                sort_key=_sort_key(ICONTAINS_SCORE, entity_type='user', label=profile_user.username),
            )
        )
    return hits, total


def global_search(
    user: User,
    query: str,
    *,
    types: set[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    term = normalize_query(query)
    search_types = types or ALL_SEARCH_TYPES
    invalid_types = search_types - ALL_SEARCH_TYPES
    if invalid_types:
        raise SearchValidationError(f'Invalid search types: {", ".join(sorted(invalid_types))}')

    limit = max(1, min(limit, 50))
    offset = max(0, offset)
    fetch_limit = min(50, offset + limit)

    searchers: dict[str, Any] = {
        'location': lambda: _search_locations(user, term, fetch_limit),
        'collection': lambda: _search_collections(user, term, fetch_limit),
        'lodging': lambda: _search_collection_entity(
            entity_type='lodging',
            model=Lodging,
            user=user,
            term=term,
            vector_fields=('name', 'description', 'location'),
            fetch_limit=fetch_limit,
        ),
        'transportation': lambda: _search_collection_entity(
            entity_type='transportation',
            model=Transportation,
            user=user,
            term=term,
            vector_fields=('name', 'description', 'from_location', 'to_location'),
            fetch_limit=fetch_limit,
        ),
        'note': lambda: _search_collection_entity(
            entity_type='note',
            model=Note,
            user=user,
            term=term,
            vector_fields=('name', 'content'),
            fetch_limit=fetch_limit,
        ),
        'checklist': lambda: _search_collection_entity(
            entity_type='checklist',
            model=Checklist,
            user=user,
            term=term,
            vector_fields=('name',),
            fetch_limit=fetch_limit,
        ),
        'activity': lambda: _search_activities(user, term, fetch_limit),
        'country': lambda: _search_countries(term, fetch_limit),
        'region': lambda: _search_regions(user, term, fetch_limit),
        'city': lambda: _search_cities(user, term, fetch_limit),
        'user': lambda: _search_users(term, fetch_limit),
    }

    all_hits: list[SearchHit] = []
    facets: dict[str, int] = {}

    for search_type in sorted(search_types):
        hits, total = searchers[search_type]()
        facets[search_type] = total
        all_hits.extend(hits)

    # Locations first, then collections, then other user content, then reference data.
    all_hits.sort(key=lambda hit: hit.sort_key, reverse=True)
    total = sum(facets.values())
    page_hits = all_hits[offset : offset + limit]

    return {
        'query': term,
        'total': total,
        'limit': limit,
        'offset': offset,
        'results': [hit.to_dict() for hit in page_hits],
        'facets': facets,
    }
