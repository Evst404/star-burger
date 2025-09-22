from django.db import migrations
from django.db.models import Count


def remove_duplicate_products(apps, schema_editor):
    Product = apps.get_model('foodcartapp', 'Product')
    duplicates = Product.objects.values('name').annotate(count=Count('id')).filter(count__gt=1)
    for dup in duplicates:
        name = dup['name']
        products = Product.objects.filter(name=name).order_by('id')
        for product in products[1:]:  
            product.delete()


def reverse_remove_duplicate_products(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('foodcartapp', '0041_auto_20250919_2010'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_products, reverse_remove_duplicate_products),
    ]