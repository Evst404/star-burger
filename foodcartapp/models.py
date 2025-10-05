from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import F, Sum, Count, Q
from phonenumber_field.modelfields import PhoneNumberField


class Restaurant(models.Model):
    name = models.CharField(
        verbose_name='название',
        max_length=50,
        blank=False,
        null=False
    )
    address = models.CharField(
        verbose_name='адрес',
        max_length=100,
        blank=True,
        null=False,
        default=''
    )
    contact_phone = models.CharField(
        verbose_name='контактный телефон',
        max_length=50,
        blank=True,
        null=False,
        default=''
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        verbose_name='название',
        max_length=50,
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        verbose_name='название',
        max_length=50,
        blank=False,
        null=False,
        unique=True
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        verbose_name='цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    image = models.ImageField(
        verbose_name='картинка',
        blank=False,
        null=False
    )
    special_status = models.BooleanField(
        verbose_name='спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        verbose_name='описание',
        blank=True,
        null=False,
        default=''
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name='ресторан',
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        verbose_name='в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [['restaurant', 'product']]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(F('items__price') * F('items__quantity'))
        )

    def with_available_restaurants(self):
        order_ids = self.values_list('id', flat=True)
        order_products = OrderItem.objects.filter(order__in=order_ids).values('order_id', 'product_id')
        
        available_restaurants = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values('restaurant')
            .annotate(product_count=Count('product'))
            .filter(product_count=Count('product', filter=Q(product__order_items__order__in=order_ids)))
        )
        
        return self.prefetch_related(
            models.Prefetch(
                'restaurant',
                queryset=Restaurant.objects.filter(id__in=available_restaurants.values('restaurant'))
            )
        )


class Order(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'Принят'),
        ('COOKING', 'Готовится'),
        ('DELIVERING', 'Доставляется'),
        ('COMPLETED', 'Завершён'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Наличными'),
        ('ONLINE', 'Электронно'),
    ]

    firstname = models.CharField(
        verbose_name='Имя',
        max_length=50,
        blank=False,
        null=False,
        db_index=True
    )
    lastname = models.CharField(
        verbose_name='Фамилия',
        max_length=50,
        blank=False,
        null=False,
        db_index=True
    )
    phonenumber = PhoneNumberField(
        verbose_name='Номер телефона',
        blank=False,
        null=False,
        db_index=True
    )
    address = models.CharField(
        verbose_name='Адрес доставки',
        max_length=200,
        blank=False,
        null=False,
        db_index=True
    )
    status = models.CharField(
        verbose_name='Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='NEW',
        db_index=True
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        null=False,
        default=''
    )
    created_at = models.DateTimeField(
        verbose_name='Дата создания',
        auto_now_add=True,
        db_index=True
    )
    called_at = models.DateTimeField(
        verbose_name='Дата звонка',
        null=True,
        blank=True,
        db_index=True
    )
    delivered_at = models.DateTimeField(
        verbose_name='Дата доставки',
        null=True,
        blank=True,
        db_index=True
    )
    payment_method = models.CharField(
        verbose_name='Способ оплаты',
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        blank=False,
        null=False,
        db_index=True
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name='Ресторан, который приготовит заказ',
        related_name='restaurant_orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-id']

    def __str__(self):
        return f'Заказ {self.id} ({self.firstname} {self.lastname})'

    def available_restaurants(self):
        if hasattr(self, '_prefetched_objects_cache') and 'restaurant' in self._prefetched_objects_cache:
            return self._prefetched_objects_cache['restaurant']
        return []


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name='Заказ',
        on_delete=models.CASCADE,
        related_name='items',
        blank=False,
        null=False
    )
    product = models.ForeignKey(
        Product,
        verbose_name='Продукт',
        on_delete=models.PROTECT,
        related_name='order_items',
        blank=False,
        null=False
    )
    quantity = models.PositiveIntegerField(
        verbose_name='Количество',
        blank=False,
        null=False,
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        verbose_name='Цена на момент заказа',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        blank=False,
        null=False
    )

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        ordering = ['id']

    def __str__(self):
        return f'{self.product.name} ({self.quantity} шт.)'