"""Routers for resources the router's default list/detail pair does not describe."""

from rest_framework.routers import DynamicRoute, Route, SimpleRouter


class SingletonRouter(SimpleRouter):
    """
    Routes a viewset that manages one object per user (or per parent) at a single path.

        GET    /prefix/   -> retrieve
        POST   /prefix/   -> create
        PUT    /prefix/   -> update
        PATCH  /prefix/   -> partial_update
        DELETE /prefix/   -> destroy
        *      /prefix/<url_path>/ -> @action(detail=False) methods

    Only methods the viewset defines are routed. The viewset finds its object itself
    (``get_object``) instead of reading a primary key from the URL.
    """

    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'retrieve',
                'post': 'create',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy',
            },
            name='{basename}',
            detail=False,
            initkwargs={'suffix': 'Instance'},
        ),
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={},
        ),
    ]
