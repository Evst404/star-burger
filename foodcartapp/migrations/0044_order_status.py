from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('foodcartapp', '0043_alter_product_name'), 
    ]

    operations = [
        migrations.AddField(
            model_name='Order',
            name='status',
            field=models.CharField(
                choices=[('NEW', 'Принят'), ('COOKING', 'Готовится'), ('DELIVERING', 'Доставляется'), ('COMPLETED', 'Завершён')],
                default='NEW',
                max_length=20,
                verbose_name='Статус',
                db_index=True,
            ),
        ),
    ]