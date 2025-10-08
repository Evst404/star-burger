from django.db import transaction
from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber
from .models import Order, OrderItem, Product
import re


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']
        read_only_fields = ['price']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше 0.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    products = OrderItemSerializer(many=True, source='items', allow_empty=False)

    class Meta:
        model = Order
        fields = [
            'id',
            'firstname',
            'lastname',
            'phonenumber',
            'address',
            'products',
            'comment',
            'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_phonenumber(self, value):
        if not value:
            raise serializers.ValidationError("Это поле не может быть пустым.")
        try:
            phone_number = PhoneNumber.from_string(value)
            if not phone_number.is_valid():
                raise serializers.ValidationError("Введен некорректный номер телефона.")
        except Exception:
            raise serializers.ValidationError("Введен некорректный номер телефона.")
        return value

    def validate_address(self, value):
        if not value:
            raise serializers.ValidationError("Адрес не может быть пустым.")
        pattern = r'^\s*[А-Яа-яЁёA-Za-z\s]+,\s*[А-Яа-яЁёA-Za-z\s\.]+\s*\d+[А-Яа-яЁё]?\s*$'
        if not re.match(pattern, value.strip()):
            raise serializers.ValidationError(
                "Адрес должен быть в формате: 'Город, улица, номер дома' (например, 'Москва, ул. Ленина, 1')."
            )
        return value.strip()

    def create(self, validated_data):
        with transaction.atomic():
            items_data = validated_data.pop('items')
            if isinstance(validated_data['phonenumber'], PhoneNumber):
                validated_data['phonenumber'] = str(validated_data['phonenumber'])
            validated_data.setdefault('comment', '')
            order = Order.objects.create(**validated_data)
            for item_data in items_data:
                product = item_data['product']
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item_data['quantity'],
                    price=product.price
                )
            return order