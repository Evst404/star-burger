from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('foodcartapp', '0044_order_status'), 
    ]

    operations = [
        migrations.AddField(
            model_name='Order',
            name='comment',
            field=models.TextField(
                verbose_name='Комментарий',
                blank=True,
                null=False,
                default=''
            ),
        ),
    ]