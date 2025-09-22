from django.db import migrations
from django.core.cache import cache


def fill_orderitem_prices(apps, schema_editor):
    cache.clear()  
    OrderItem = apps.get_model('foodcartapp', 'OrderItem')
    for order_item in OrderItem.objects.select_related('product').all():
        order_item.price = order_item.product.price if order_item.product else 0.00
        order_item.save(update_fields=['price'])


def reverse_fill_orderitem_prices(apps, schema_editor):
    OrderItem = apps.get_model('foodcartapp', 'OrderItem')
    OrderItem.objects.update(price=0)


class Migration(migrations.Migration):
    dependencies = [
        ('foodcartapp', '0040_orderitem_price'),  
    ]

    operations = [
        migrations.RunPython(fill_orderitem_prices, reverse_fill_orderitem_prices),
    ]