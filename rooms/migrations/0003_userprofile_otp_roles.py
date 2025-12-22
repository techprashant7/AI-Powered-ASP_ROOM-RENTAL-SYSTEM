from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0002_userprofile_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='otp_code',
            field=models.CharField(blank=True, max_length=6),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='otp_created_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='staff_requested',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='staff_approved',
            field=models.BooleanField(default=False),
        ),
    ]
