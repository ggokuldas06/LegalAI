from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_chatlog_document'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add v2.0 fields to Document
        migrations.AddField(
            model_name='document',
            name='file_type',
            field=models.CharField(
                choices=[('pdf', 'PDF'), ('image', 'Image'), ('text', 'Text')],
                default='pdf',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='document',
            name='page_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='document',
            name='doc_description',
            field=models.TextField(blank=True),
        ),
        # Create Case model
        migrations.CreateModel(
            name='Case',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cases',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'cases',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='case',
            index=models.Index(fields=['user', '-updated_at'], name='cases_user_updated_idx'),
        ),
        # Create CaseDocument junction
        migrations.CreateModel(
            name='CaseDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[
                        ('primary', 'Primary Document'),
                        ('evidence', 'Evidence'),
                        ('reference', 'Reference'),
                        ('contract', 'Contract'),
                        ('exhibit', 'Exhibit'),
                        ('other', 'Other'),
                    ],
                    default='other',
                    max_length=20,
                )),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('case', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='case_documents',
                    to='api.case',
                )),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='case_documents',
                    to='api.document',
                )),
            ],
            options={
                'db_table': 'case_documents',
                'ordering': ['added_at'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='casedocument',
            unique_together={('case', 'document')},
        ),
        # Add M2M through field on Case
        migrations.AddField(
            model_name='case',
            name='documents',
            field=models.ManyToManyField(
                blank=True,
                related_name='cases',
                through='api.CaseDocument',
                to='api.document',
            ),
        ),
        # Update ChatLog mode choices to include D
        migrations.AlterField(
            model_name='chatlog',
            name='mode',
            field=models.CharField(
                choices=[
                    ('A', 'Summarizer'),
                    ('B', 'Clause Classifier'),
                    ('C', 'Case-Law IRAC'),
                    ('D', 'Case Agentic Q&A'),
                ],
                max_length=1,
            ),
        ),
    ]
