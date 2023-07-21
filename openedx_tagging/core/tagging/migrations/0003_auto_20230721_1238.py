# Generated by Django 3.2.19 on 2023-07-21 17:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oel_tagging', '0002_auto_20230718_2026'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelObjectTag',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.objecttag',),
        ),
        migrations.CreateModel(
            name='SystemDefinedTaxonomy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.taxonomy',),
        ),
        migrations.RemoveField(
            model_name='taxonomy',
            name='system_defined',
        ),
        migrations.CreateModel(
            name='LanguageTaxonomy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.systemdefinedtaxonomy',),
        ),
        migrations.CreateModel(
            name='ModelSystemDefinedTaxonomy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.systemdefinedtaxonomy',),
        ),
        migrations.CreateModel(
            name='UserModelObjectTag',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.modelobjecttag',),
        ),
        migrations.CreateModel(
            name='UserSystemDefinedTaxonomy',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('oel_tagging.modelsystemdefinedtaxonomy',),
        ),
    ]
