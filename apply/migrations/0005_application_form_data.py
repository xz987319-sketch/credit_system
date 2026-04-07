# Generated manually for adding form_data JSONField to Application model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apply', '0004_formpage_order_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='form_data',
            field=models.JSONField(blank=True, null=True, verbose_name='动态表单数据'),
        ),
    ]
