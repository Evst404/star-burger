from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from foodcartapp.models import Product, Restaurant, Order, RestaurantMenuItem
from geopy.distance import geodesic
from places.models import Place
from django.utils import timezone
from datetime import timedelta
import requests
from django.conf import settings


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")
        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))
    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]
        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )
    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


def geocode_address(address):
    if not settings.YANDEX_GEOCODER_API_KEY:
        return None, None
    url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&geocode={address}&format=json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        collection = data.get('response', {}).get('GeoObjectCollection', {})
        if collection.get('metaDataProperty', {}).get('GeocoderMetaData', {}).get('found', 0) > 0:
            point = collection['featureMember'][0]['GeoObject']['Point']['pos']
            lon, lat = map(float, point.split())
            return lat, lon
        return None, None
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None, None


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = Order.objects.with_total_price().prefetch_related('items__product', 'restaurant').exclude(status='COMPLETED').order_by('-id')
    for order in orders:
        order.available_restaurants_list = order.available_restaurants()
        place, created = Place.objects.get_or_create(address=order.address)
        if created or place.last_updated < timezone.now() - timedelta(days=30):
            lat, lon = geocode_address(order.address)
            place.latitude = lat
            place.longitude = lon
            place.last_updated = timezone.now()
            place.save()
            order.latitude = lat
            order.longitude = lon
        else:
            order.latitude = place.latitude
            order.longitude = place.longitude
        for restaurant in order.available_restaurants_list:
            restaurant_place, created = Place.objects.get_or_create(address=restaurant.address)
            if created or restaurant_place.last_updated < timezone.now() - timedelta(days=30):
                lat, lon = geocode_address(restaurant.address)
                restaurant_place.latitude = lat
                restaurant_place.longitude = lon
                restaurant_place.last_updated = timezone.now()
                restaurant_place.save()
                restaurant.latitude = lat
                restaurant.longitude = lon
            else:
                restaurant.latitude = restaurant_place.latitude
                restaurant.longitude = restaurant_place.longitude
            if order.latitude and order.longitude and restaurant.latitude and restaurant.longitude:
                distance = geodesic((order.latitude, order.longitude), (restaurant.latitude, restaurant.longitude)).km
                restaurant.distance_km = round(distance, 1)
            else:
                restaurant.distance_km = None
        order.available_restaurants_list = sorted(order.available_restaurants_list, key=lambda r: r.distance_km or float('inf'))
    return render(request, template_name='order_items.html', context={
        'order_items': orders
    })