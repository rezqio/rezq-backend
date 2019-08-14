# Generated by Django 2.1.5 on 2019-02-08 05:05

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import rezq.models.user
import rezq.validators
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('username', models.CharField(blank=True, db_index=True, error_messages={'unique': 'A user with that username already exists.'}, help_text='64 characters or fewer. Letters and digits only.', max_length=64, null=True, unique=True, validators=[django.core.validators.RegexValidator('^[0-9a-zA-Z]*$', 'Only alphanumeric characters are allowed.')], verbose_name='username')),
                ('email', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name='email address')),
                ('unverified_email', models.EmailField(blank=True, db_index=True, max_length=254, null=True, unique=True, verbose_name='unverified email address')),
                ('password', models.CharField(blank=True, max_length=128, null=True, verbose_name='password')),
                ('waterloo_id', models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True, verbose_name='waterloo user id')),
                ('facebook_id', models.CharField(blank=True, db_index=True, max_length=24, null=True, unique=True, verbose_name='facebook user id')),
                ('google_id', models.CharField(blank=True, db_index=True, max_length=24, null=True, unique=True, verbose_name='google user id')),
                ('industries', models.TextField(blank=True, default='', validators=[rezq.validators.validate_industries])),
                ('email_subscribed', models.BooleanField(default=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_premium', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', rezq.models.user.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CritiquerRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('industries', models.TextField(validators=[rezq.validators.validate_industries])),
                ('critiquer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LinkedCritique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('summary', models.TextField(blank=True, default='')),
                ('annotations', models.TextField(default='[]')),
                ('submitted', models.BooleanField(db_index=True, default=False)),
                ('submitted_on', models.DateTimeField(blank=True, null=True)),
                ('critiquer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='LinkedCritiqueComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('comment', models.CharField(max_length=1024)),
                ('critique', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.LinkedCritique')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MatchedCritique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('summary', models.TextField(blank=True, default='')),
                ('annotations', models.TextField(default='[]')),
                ('submitted', models.BooleanField(db_index=True, default=False)),
                ('submitted_on', models.DateTimeField(blank=True, null=True)),
                ('matched_on', models.DateTimeField(blank=True, null=True)),
                ('critiquer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MatchedCritiqueComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('comment', models.CharField(max_length=1024)),
                ('critique', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.MatchedCritique')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MockS3File',
            fields=[
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='mock-s3/')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PageReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('pathname', models.CharField(max_length=128)),
                ('search', models.CharField(blank=True, max_length=512, null=True)),
                ('message', models.CharField(max_length=1024)),
                ('reply_to', models.EmailField(blank=True, max_length=254, null=True)),
                ('reporter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PooledCritique',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('summary', models.TextField(blank=True, default='')),
                ('annotations', models.TextField(default='[]')),
                ('submitted', models.BooleanField(db_index=True, default=False)),
                ('submitted_on', models.DateTimeField(blank=True, null=True)),
                ('critiquer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PooledCritiqueComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('comment', models.CharField(max_length=1024)),
                ('critique', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.PooledCritique')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PooledCritiqueVote',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('is_upvote', models.BooleanField(default=True)),
                ('critique', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.PooledCritique')),
                ('voter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Resume',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=32)),
                ('description', models.CharField(blank=True, default='', max_length=256)),
                ('industries', models.TextField(validators=[rezq.validators.validate_industries])),
                ('notes_for_critiquer', models.CharField(blank=True, default='', max_length=1024)),
                ('link_enabled', models.BooleanField(default=False)),
                ('pool_enabled', models.BooleanField(db_index=True, default=False)),
                ('uploader', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='pooledcritique',
            name='resume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.Resume'),
        ),
        migrations.AddField(
            model_name='matchedcritique',
            name='resume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.Resume'),
        ),
        migrations.AddField(
            model_name='linkedcritique',
            name='resume',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rezq.Resume'),
        ),
        migrations.AlterUniqueTogether(
            name='pooledcritiquevote',
            unique_together={('voter', 'critique')},
        ),
    ]
