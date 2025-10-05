import requests
from django.conf import settings
from django.utils import timezone
from .models import Place


def geocode_addresses(addresses):
    if not settings.YANDEX_GEOCODER_API_KEY:
        return {address: (None, None) for address in addresses}
    
    results = {}
    for address in addresses:
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&geocode={address}&format=json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            payload = response.json()
            collection = payload.get('response', {}).get('GeoObjectCollection', {})
            if collection.get('metaDataProperty', {}).get('GeocoderMetaData', {}).get('found', 0) > 0:
                point = collection['featureMember'][0]['GeoObject']['Point']['pos']
                lon, lat = map(float, point.split())
                results[address] = (lat, lon)
            else:
                results[address] = (None, None)
        except (requests.exceptions.RequestException, KeyError, ValueError):
            results[address] = (None, None)
    
    for address, (lat, lon) in results.items():
        place, created = Place.objects.get_or_create(address=address)
        place.latitude = lat
        place.longitude = lon
        place.last_updated = timezone.now()
        place.save()
    
    return results