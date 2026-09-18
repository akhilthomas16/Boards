from django.db import migrations, models


def mark_existing_verified(apps, schema_editor):
    """Accounts that predate email verification keep working."""
    apps.get_model('accounts', 'UserProfile').objects.update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_existing_verified, migrations.RunPython.noop),
    ]
