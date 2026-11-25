"""Stored files that several rows can share (see "Stored files" in API.md)."""

from django.db import transaction


def delete_replaced_file(model, field_name, name):
    """
    Queue removal of the stored file ``name`` that an update of a ``model`` row replaced, once the
    update commits, so a rolled-back update keeps it. Like a row delete (``adventures.signals``),
    the file stays while another row still uses it.
    """
    if not name:
        return
    from adventures.tasks import delete_stored_file

    transaction.on_commit(
        lambda: delete_stored_file.defer(model_label=model._meta.label, field_name=field_name, name=name)
    )
