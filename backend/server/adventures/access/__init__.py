"""Who may read or change what: the rules behind the API permissions.

``audience`` resolves a request's role in a collection (owner, editor, viewer, guest link);
``file_permissions`` decides who may fetch a stored file; ``location`` decides who may read
a place. The DRF permission classes in ``adventures.permissions`` are built on these.
"""
