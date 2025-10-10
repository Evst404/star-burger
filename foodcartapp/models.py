from collections import defaultdict

import logging
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Sum
from phonenumber_field.modelfields import PhoneNumberField

logger = logging.getLogger(__name__)


class Restaurant(models.Model):
    name = models.CharField("название", max_length=50)
    address = models.CharField("адрес", max_length=100, default="")
    contact_phone = models.CharField("контактный телефон", max_length=50, default="")

    class Meta:
        verbose_name = "ресторан"
        verbose_name_plural = "рестораны"

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = RestaurantMenuItem.objects.filter(availability=True).values_list(
            "product", flat=True
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField("название", max_length=50)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("название", max_length=50, unique=True)
    category = models.ForeignKey(
        ProductCategory,
        verbose_name="категория",
        related_name="products",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        "цена", max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    image = models.ImageField("картинка")
    special_status = models.BooleanField("спец.предложение", default=False, db_index=True)
    description = models.TextField("описание")

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name="ресторан",
        related_name="menu_items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        verbose_name="продукт",
        related_name="menu_items",
        on_delete=models.CASCADE,
    )
    availability = models.BooleanField("в продаже", default=True, db_index=True)

    class Meta:
        verbose_name = "пункт меню ресторана"
        verbose_name_plural = "пункты меню ресторана"
        unique_together = [["restaurant", "product"]]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(total_price=Sum(F("items__price") * F("items__quantity")))

    def with_available_restaurants(self):
        menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related(
            "restaurant", "product"
        )
        rests_with_products = defaultdict(set)
        for item in menu_items:
            rests_with_products[item.restaurant].add(item.product_id)

        for order in self:
            order_products = set(item.product_id for item in order.items.all())
            available_restaurants = [
                rest
                for rest, rest_products in rests_with_products.items()
                if order_products.issubset(rest_products)
            ]
            logger.debug(
                f"Order {order.id}: products {order_products}, "
                f"available restaurants {[r.name for r in available_restaurants]}"
            )
            setattr(order, "available_restaurants", available_restaurants)
        return self


class Order(models.Model):
    STATUS_CHOICES = [
        ("UNPROCESSED", "Необработан"),
        ("NEW", "Принят"),
        ("COOKING", "Готовится"),
        ("DELIVERING", "Доставляется"),
        ("COMPLETED", "Завершён"),
    ]
    PAYMENT_METHOD_CHOICES = [("CASH", "Наличными"), ("ONLINE", "Электронно")]

    firstname = models.CharField("Имя", max_length=50, db_index=True)
    lastname = models.CharField("Фамилия", max_length=50, db_index=True)
    phonenumber = PhoneNumberField("Номер телефона", db_index=True)
    address = models.CharField("Адрес доставки", max_length=200, db_index=True)
    status = models.CharField(
        verbose_name="Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="UNPROCESSED",
        db_index=True,
    )
    comment = models.TextField("Комментарий", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True, db_index=True)
    called_at = models.DateTimeField("Дата звонка", null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField(
        "Дата доставки", null=True, blank=True, db_index=True
    )
    payment_method = models.CharField(
        verbose_name="Способ оплаты",
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        db_index=True,
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name="Ресторан, который приготовит заказ",
        related_name="restaurant_orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-id"]

    def __str__(self):
        return f"Заказ {self.id} ({self.firstname} {self.lastname})"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name="Заказ",
        related_name="items",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        verbose_name="Продукт",
        related_name="order_items",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(
        "Количество", validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        "Цена на момент заказа",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказа"
        ordering = ["id"]

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"