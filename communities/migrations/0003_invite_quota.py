from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("communities", "0002_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="membership",
            name="extra_invites",
            field=models.PositiveIntegerField(default=0, verbose_name="convites extras"),
        ),
        migrations.AlterField(
            model_name="event",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="preço"),
        ),
        migrations.AlterField(
            model_name="invitation",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254, verbose_name="e-mail"),
        ),
    ]
