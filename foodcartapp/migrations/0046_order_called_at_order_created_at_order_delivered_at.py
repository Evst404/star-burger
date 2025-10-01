from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0045_order_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='Order',
            name='called_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Дата звонка'
            ),
        ),
        migrations.AddField(
            model_name='Order',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                verbose_name='Дата создания'
            ),
        ),
        migrations.AddField(
            model_name='Order',
            name='delivered_at',
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name='Дата доставки'
            ),
        ),
    ]