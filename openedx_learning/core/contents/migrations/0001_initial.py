# Generated by Django 3.2.23 on 2023-12-04 00:41

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import openedx_learning.lib.fields
import openedx_learning.lib.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('oel_publishing', '0002_alter_fk_on_delete'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaType',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('type', openedx_learning.lib.fields.MultiCollationCharField(db_collations={'mysql': 'utf8mb4_unicode_ci', 'sqlite': 'NOCASE'}, max_length=127)),
                ('sub_type', openedx_learning.lib.fields.MultiCollationCharField(db_collations={'mysql': 'utf8mb4_unicode_ci', 'sqlite': 'NOCASE'}, max_length=127)),
                ('suffix', openedx_learning.lib.fields.MultiCollationCharField(blank=True, db_collations={'mysql': 'utf8mb4_unicode_ci', 'sqlite': 'NOCASE'}, max_length=127)),
            ],
        ),
        migrations.CreateModel(
            name='RawContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hash_digest', models.CharField(editable=False, max_length=40)),
                ('size', models.PositiveBigIntegerField(validators=[django.core.validators.MaxValueValidator(50000000)])),
                ('created', models.DateTimeField(validators=[openedx_learning.lib.validators.validate_utc_datetime])),
                ('file', models.FileField(null=True, upload_to='')),
                ('learning_package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='oel_publishing.learningpackage')),
                ('media_type', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='oel_contents.mediatype')),
            ],
            options={
                'verbose_name': 'Raw Content',
                'verbose_name_plural': 'Raw Contents',
            },
        ),
        migrations.CreateModel(
            name='TextContent',
            fields=[
                ('raw_content', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='text_content', serialize=False, to='oel_contents.rawcontent')),
                ('text', openedx_learning.lib.fields.MultiCollationTextField(blank=True, db_collations={'mysql': 'utf8mb4_bin', 'sqlite': 'BINARY'}, max_length=100000)),
                ('length', models.PositiveIntegerField()),
            ],
        ),
        migrations.AddConstraint(
            model_name='mediatype',
            constraint=models.UniqueConstraint(fields=('type', 'sub_type', 'suffix'), name='oel_contents_uniq_t_st_sfx'),
        ),
        migrations.AddIndex(
            model_name='rawcontent',
            index=models.Index(fields=['learning_package', 'media_type'], name='oel_content_idx_lp_media_type'),
        ),
        migrations.AddIndex(
            model_name='rawcontent',
            index=models.Index(fields=['learning_package', '-size'], name='oel_content_idx_lp_rsize'),
        ),
        migrations.AddIndex(
            model_name='rawcontent',
            index=models.Index(fields=['learning_package', '-created'], name='oel_content_idx_lp_rcreated'),
        ),
        migrations.AddConstraint(
            model_name='rawcontent',
            constraint=models.UniqueConstraint(fields=('learning_package', 'media_type', 'hash_digest'), name='oel_content_uniq_lc_media_type_hash_digest'),
        ),
    ]
