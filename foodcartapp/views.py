from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.templatetags.static import static
from .models import Product
from .serializers import OrderSerializer
import logging


logger = logging.getLogger(__name__)


@api_view(['GET'])
def banners_list_api(request):  
    return Response([
        {
            'title': 'Burger',
            'src': static('food.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ])


@api_view(['GET'])
def product_list_api(request):  
    products = Product.objects.select_related('category').available().prefetch_related('menu_items__restaurant')
    serialized_products = [
        {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurants': [
                {
                    'id': menu_item.restaurant.id,
                    'name': menu_item.restaurant.name,
                } for menu_item in product.menu_items.filter(availability=True)
            ]
        } for product in products
    ]
    return Response(serialized_products)


@api_view(['POST'])
def register_order(request):
    logger.info(f"Получен запрос на создание заказа: {request.data}")
    serializer = OrderSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.save()
        output_serializer = OrderSerializer(order)
        logger.info(f"Заказ успешно создан: {output_serializer.data}")
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    logger.error(f"Ошибка валидации заказа: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)