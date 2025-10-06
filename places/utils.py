import logging
import requests
import time
from django.conf import settings
from django.utils import timezone
from .models import Place


logger = logging.getLogger(__name__)


def geocode_addresses(addresses):
    if not settings.YANDEX_GEOCODER_API_KEY:
        logger.error("Отсутствует YANDEX_GEOCODER_API_KEY")
        return {address: (None, None) for address in addresses}

    addresses_list = list(set(addresses))
    logger.info(f"Геокодирование {len(addresses_list)} адресов")

    existing_places = Place.objects.filter(address__in=addresses_list)
    existing_coords = {place.address: (place.latitude, place.longitude) for place in existing_places}

    addresses_to_geocode = [addr for addr in addresses_list if addr not in existing_coords or not all(existing_coords[addr])]
    results = {addr: existing_coords.get(addr, (None, None)) for addr in addresses_list}

    for address in addresses_to_geocode:
        logger.info(f"Геокодирование адреса: {address}")
        url = f"https://geocode-maps.yandex.ru/1.x/?apikey={settings.YANDEX_GEOCODER_API_KEY}&geocode={address}&format=json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in (403, 429):
                logger.error(f"Ошибка {response.status_code} для {address}")
                results[address] = (None, None)
                continue
            response.raise_for_status()
            payload = response.json()
            collection = payload.get('response', {}).get('GeoObjectCollection', {})
            meta = collection.get('metaDataProperty', {}).get('GeocoderResponseMetaData', {})
            found = meta.get('found', '0')

            if int(found) > 0:
                feature = collection.get('featureMember', [{}])[0].get('GeoObject', {})
                precision = feature.get('metaDataProperty', {}).get('GeocoderMetaData', {}).get('precision', '')
                if precision == 'exact':
                    point = feature.get('Point', {}).get('pos', '')
                    if point:
                        lon, lat = map(float, point.split())
                        results[address] = (lat, lon)
                        Place.objects.update_or_create(
                            address=address,
                            defaults={'latitude': lat, 'longitude': lon, 'last_updated': timezone.now()}
                        )
                    else:
                        results[address] = (None, None)
                else:
                    results[address] = (None, None)
            else:
                results[address] = (None, None)
            time.sleep(0.1)
        except requests.RequestException as e:
            logger.error(f"Ошибка запроса для {address}: {str(e)}")
            results[address] = (None, None)
        except (KeyError, ValueError) as e:
            logger.error(f"Ошибка обработки для {address}: {str(e)}")
            results[address] = (None, None)

    return results