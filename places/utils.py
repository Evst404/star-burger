import logging
import time

import requests
from django.conf import settings
from django.utils import timezone

from .models import Place

logger = logging.getLogger(__name__)


VALID_ADDRESS_KINDS = {"house", "street", "locality"}


def geocode_addresses(addresses):
    if not settings.YANDEX_GEOCODER_API_KEY:
        logger.error("Отсутствует YANDEX_GEOCODER_API_KEY")
        return {address: (None, None) for address in addresses}

    addresses_list = list(set(addresses))
    logger.info(f"Геокодирование {len(addresses_list)} адресов")

    existing_places = Place.objects.filter(address__in=addresses_list)
    existing_coords = {
        place.address: (place.latitude, place.longitude) for place in existing_places
    }
    addresses_to_geocode = [
        addr
        for addr in addresses_list
        if addr not in existing_coords or not all(existing_coords[addr])
    ]
    results = {addr: existing_coords.get(addr, (None, None)) for addr in addresses_list}

    for address in addresses_to_geocode:
        logger.info(f"Геокодирование адреса: {address}")
        base_url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": settings.YANDEX_GEOCODER_API_KEY,
            "geocode": address,
            "format": "json",
        }
        try:
            response = requests.get(base_url, params=params, timeout=5)
            if response.status_code in (403, 429):
                logger.error(f"Ошибка {response.status_code} для {address}")
                results[address] = (None, None)
                continue
            response.raise_for_status()
            payload = response.json()
            found_places = payload.get("response", {}).get(
                "GeoObjectCollection", {}
            ).get("featureMember")
            if not found_places:
                logger.info(f"Адрес {address} не найден")
                results[address] = (None, None)
                continue
            feature = found_places[0].get("GeoObject", {})
            kind = feature.get("metaDataProperty", {}).get(
                "GeocoderMetaData", {}
            ).get("kind", "")
            precision = feature.get("metaDataProperty", {}).get(
                "GeocoderMetaData", {}
            ).get("precision", "")
            address_text = feature.get("metaDataProperty", {}).get(
                "GeocoderMetaData", {}
            ).get("text", "")
            point = feature.get("Point", {}).get("pos", "")
            if point and kind in VALID_ADDRESS_KINDS and address.lower() in address_text.lower():
                lon, lat = map(float, point.split())
                if precision != "exact" and kind == "locality":
                    logger.info(
                        f"Адрес {address} определён как город, используются примерные координаты"
                    )
                logger.debug(
                    f"Успешное геокодирование: {address}, kind: {kind}, "
                    f"precision: {precision}, coords: ({lat}, {lon})"
                )
                results[address] = (lat, lon)
                Place.objects.update_or_create(
                    address=address,
                    defaults={
                        "latitude": lat,
                        "longitude": lon,
                        "last_updated": timezone.now(),
                    },
                )
            else:
                logger.info(
                    f"Адрес {address} невалиден (kind: {kind}, text: {address_text})"
                )
                results[address] = (None, None)
            time.sleep(0.1)
        except requests.RequestException as e:
            logger.error(f"Ошибка запроса для {address}: {str(e)}")
            results[address] = (None, None)
        except (KeyError, ValueError) as e:
            logger.error(f"Ошибка обработки для {address}: {str(e)}")
            results[address] = (None, None)

    return results