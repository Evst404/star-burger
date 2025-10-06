from django.contrib import admin
from django.shortcuts import reverse, redirect
from django.templatetags.static import static
from django.utils.html import format_html
from django.db import transaction
from django.utils.http import url_has_allowed_host_and_scheme
from .models import Product, ProductCategory, Restaurant, RestaurantMenuItem, Order, OrderItem


class RestaurantMenuItemInline(admin.TabularInline):
    model = RestaurantMenuItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    search_fields = ['name', 'address', 'contact_phone']
    list_display = ['name', 'address', 'contact_phone']
    inlines = [RestaurantMenuItemInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['get_image_list_preview', 'name', 'category', 'price']
    list_display_links = ['name']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    inlines = [RestaurantMenuItemInline]
    fieldsets = (
        ('Общее', {
            'fields': ['name', 'category', 'image', 'get_image_preview', 'price']
        }),
        ('Подробно', {
            'fields': ['special_status', 'description'],
            'classes': ['wide'],
        }),
    )
    readonly_fields = ['get_image_preview']

    class Media:
        css = {"all": (static("admin/foodcartapp.css"),)}

    def get_image_preview(self, obj):
        if not obj.image:
            return 'выберите картинку'
        return format_html('<img src="{url}" style="max-height: 200px;"/>', url=obj.image.url)
    get_image_preview.short_description = 'превью'

    def get_image_list_preview(self, obj):
        if not obj.image or not obj.id:
            return 'нет картинки'
        edit_url = reverse('admin:foodcartapp_product_change', args=(obj.id,))
        return format_html('<a href="{edit_url}"><img src="{src}" style="max-height: 50px;"/></a>',
                           edit_url=edit_url, src=obj.image.url)
    get_image_list_preview.short_description = 'превью'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'firstname',
        'lastname',
        'phonenumber',
        'address',
        'status',
        'get_status_display',
        'comment',
        'created_at',
        'called_at',
        'delivered_at',
        'payment_method',
        'get_payment_method_display',
        'restaurant',
    ]
    list_filter = ['status', 'created_at', 'called_at', 'delivered_at', 'payment_method', 'restaurant']
    search_fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'comment']
    inlines = [OrderItemInline]
    fields = [
        'firstname',
        'lastname',
        'phonenumber',
        'address',
        'status',
        'comment',
        'payment_method',
        'restaurant',
        'called_at',
        'delivered_at',
    ]
    readonly_fields = ['created_at']

    def save_model(self, request, obj, form, change):
        if obj.restaurant and obj.status == 'UNPROCESSED':
            obj.status = 'NEW'
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        with transaction.atomic():
            instances = formset.save(commit=False)
            for instance in instances:
                if isinstance(instance, OrderItem):
                    instance.price = instance.product.price
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            formset.save_m2m()

    def response_change(self, request, obj):
        next_url = request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            return redirect(next_url)
        return super().response_change(request, obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'restaurant' and request.resolver_match.args:
            order_id = request.resolver_match.args[0]
            order = Order.objects.get(pk=order_id)
            available_restaurants = order.available_restaurants()
            kwargs['queryset'] = Restaurant.objects.filter(pk__in=[r.id for r in available_restaurants])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    search_fields = ('order__id', 'product__name')