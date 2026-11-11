from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import django.db.models.deletion


def preserve_legacy_accounts(apps, schema_editor):
    User = apps.get_model("auth", "User")
    IdentityProfile = apps.get_model("identity", "IdentityProfile")
    now = timezone.now()
    IdentityProfile.objects.bulk_create(
        [
            IdentityProfile(user=user, email_verified_at=now if user.email else None)
            for user in User.objects.all()
        ]
    )


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="IdentityProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email_verified_at", models.DateTimeField(blank=True, null=True)),
                ("verification_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="identity_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "perfil de identidade", "verbose_name_plural": "perfis de identidade"},
        ),
        migrations.RunPython(preserve_legacy_accounts, migrations.RunPython.noop),
        migrations.RunSQL(
            sql=(
                "CREATE UNIQUE INDEX auth_user_email_lower_unique "
                "ON auth_user (LOWER(email)) WHERE email <> ''"
            ),
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_lower_unique",
        ),
    ]
