# Generated manually for collaborative mode

import uuid
from django.conf import settings
from django.db import migrations, models, connection
import django.db.models.deletion


def create_auditlog_if_not_exists(apps, schema_editor):
    """Create AuditLog table only if it doesn't exist."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'adventures_auditlog'
            );
        """)
        exists = cursor.fetchone()[0]

        if not exists:
            cursor.execute("""
                CREATE TABLE adventures_auditlog (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    action VARCHAR(10) NOT NULL,
                    object_id UUID NOT NULL,
                    object_repr VARCHAR(200) NOT NULL,
                    changes JSONB DEFAULT '{}',
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users_customuser(id) ON DELETE SET NULL
                );
            """)
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS adventures__content_cbc498_idx
                ON adventures_auditlog (content_type_id, object_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS adventures__user_id_e35e7e_idx
                ON adventures_auditlog (user_id, timestamp);
            """)


def reverse_migration(apps, schema_editor):
    """Drop the AuditLog table."""
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS adventures_auditlog CASCADE;")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('adventures', '0074_soft_delete_fields'),
    ]

    operations = [
        migrations.RunPython(create_auditlog_if_not_exists, reverse_migration),
    ]
