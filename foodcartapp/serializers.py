from rest_framework import serializers
from phonenumber_field.phonenumber import PhoneNumber
from .models import Order, OrderItem, Product


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше 0.")
        return value


class OrderReadSerializer(serializers.ModelSerializer):
    product = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    products = OrderItemSerializer(many=True, source='items', allow_empty=False, write_only=True)
    items = OrderReadSerializer(many=True, read_only=True)
    firstname = serializers.CharField(max_length=50, allow_blank=False)
    lastname = serializers.CharField(max_length=50, allow_blank=False)
    phonenumber = serializers.CharField(allow_blank=False)
    address = serializers.CharField(max_length=200, allow_blank=False)

    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'products', 'items']

    def validate_products(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Ожидался list со значениями, но был получен \"{}\"".format(type(value).__name__))
        return value

    def validate_firstname(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Not a valid string.")
        return value

    def validate_lastname(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Not a valid string.")
        return value

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
        if not isinstance(value, str):
            raise serializers.ValidationError("Not a valid string.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        if isinstance(validated_data['phonenumber'], PhoneNumber):
            validated_data['phonenumber'] = str(validated_data['phonenumber'])
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order