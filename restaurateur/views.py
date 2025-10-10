from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from foodcartapp.models import Product, Restaurant, Order
from geopy.distance import geodesic
from places.models import Place
from places.utils import geocode_addresses


class Login(forms.Form):
    username = forms.CharField(
        label="Логин",
        max_length=75,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Укажите имя пользователя"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        max_length=75,
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        ),
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={"form": form})

    def post(self, request):
        form = Login(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")
        return render(request, "login.html", context={"form": form, "ivalid": True})


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("restaurateur:login")


def is_manager(user):
    return user.is_staff


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_products(request):
    restaurants = list(Restaurant.objects.order_by("name"))
    products = list(Product.objects.prefetch_related("menu_items"))
    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False) for restaurant in restaurants
        ]
        products_with_restaurant_availability.append((product, ordered_availability))
    return render(
        request,
        "products_list.html",
        context={
            "products_with_restaurant_availability": products_with_restaurant_availability,
            "restaurants": restaurants,
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_restaurants(request):
    return render(
        request, "restaurants_list.html", context={"restaurants": Restaurant.objects.all()}
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_orders(request):
    orders = (
        Order.objects.with_total_price()
        .exclude(status="COMPLETED")
        .order_by("-id")
        .select_related("restaurant")
        .prefetch_related("items__product")
        .with_available_restaurants()
    )
    addresses = list(orders.values_list("address", flat=True).distinct())
    addresses.extend(Restaurant.objects.values_list("address", flat=True).distinct())
    places = Place.objects.filter(address__in=addresses)
    place_coords = {place.address: (place.latitude, place.longitude) for place in places}
    coords = geocode_addresses(addresses)

    for order in orders:
        order_coords = place_coords.get(order.address, coords.get(order.address))
        available_restaurants = getattr(order, "available_restaurants", [])
        restaurants_with_distances = []
        for restaurant in available_restaurants:
            if order.address == restaurant.address:
                distance = 0
                display_distance = 0
                distance_unit = "м"
            else:
                rest_coords = place_coords.get(
                    restaurant.address, coords.get(restaurant.address)
                )
                distance = None
                display_distance = None
                distance_unit = None
                if order_coords and rest_coords:
                    try:
                        distance = geodesic(order_coords, rest_coords).meters
                        if distance > 100:
                            display_distance = round(distance / 1000, 1)
                            distance_unit = "км"
                        else:
                            display_distance = round(distance)
                            distance_unit = "м"
                    except ValueError:
                        pass
            restaurants_with_distances.append(
                {
                    "restaurant": restaurant,
                    "distance": distance,
                    "display_distance": display_distance,
                    "distance_unit": distance_unit,
                }
            )
        restaurants_with_distances.sort(
            key=lambda r: r["distance"] if r["distance"] is not None else float("inf")
        )
        setattr(order, "available_restaurants", restaurants_with_distances)

    return render(
        request, "order_items.html", context={"order_items": orders}
    )