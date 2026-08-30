from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import Site

from .models import RoadTripDayPage, RoadTripIndexPage, RoadTripPage


class RoadTripPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.home = Site.objects.get(is_default_site=True).root_page.specific
        cls.index = RoadTripIndexPage(
            title="Autovandry", slug="roadtrips", intro="Naše cesty"
        )
        cls.home.add_child(instance=cls.index)
        cls.index.save_revision().publish()

        cls.road_trip = RoadTripPage(
            title="Norsko 2026",
            slug="norsko-2026",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
            mapy_route_url="https://mapy.com/s/hodepofuza",
            intro="Cesta na sever",
            body="Výprava přes Skandinávii.",
            mapy_photos=[
                (
                    "mapy_photo",
                    {
                        "image_url": "https://d34-a.sdn.cz/fotka.jpeg",
                        "mapy_url": "https://mapy.com/s/homadadune",
                        "caption": "Výhled z cesty",
                    },
                )
            ],
        )
        cls.index.add_child(instance=cls.road_trip)
        cls.road_trip.save_revision().publish()

        cls.day = RoadTripDayPage(
            title="Den 1: Cesta na sever",
            slug="den-1",
            day_number=1,
            date=date(2026, 7, 1),
            mapy_route_url="https://mapy.com/s/hodepofuza",
            intro="Vyrážíme",
            body="První den na cestě.",
            mapy_photos=[
                (
                    "mapy_photo",
                    {
                        "image_url": "https://d34-a.sdn.cz/den-1.jpeg",
                        "mapy_url": "https://mapy.com/s/homadadune",
                        "caption": "První zastávka",
                    },
                )
            ],
        )
        cls.road_trip.add_child(instance=cls.day)
        cls.day.save_revision().publish()

    def test_index_lists_road_trips(self):
        response = self.client.get(self.index.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Norsko 2026")

    def test_road_trip_lists_days(self):
        response = self.client.get(self.road_trip.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Den 1: Cesta na sever")
        self.assertContains(response, "Výhled z cesty")
        self.assertContains(response, 'rel="noopener noreferrer"')
        self.assertContains(response, 'src="https://mapy.com/s/hodepofuza"')
        self.assertContains(response, "Mapa trasy – Norsko 2026")
        self.assertContains(response, 'width="1200"')
        self.assertContains(response, 'height="768"')

    def test_day_page_links_back_to_road_trip(self):
        response = self.client.get(self.day.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Norsko 2026")
        self.assertContains(response, "První den na cestě.")
        self.assertContains(response, "První zastávka")
        self.assertContains(response, "https://mapy.com/s/homadadune")
        self.assertContains(response, 'src="https://mapy.com/s/hodepofuza"')
        self.assertContains(response, "Mapa trasy – Den 1: Cesta na sever")

    def test_end_date_cannot_precede_start_date(self):
        invalid_trip = RoadTripPage(
            title="Neplatná cesta",
            start_date=date(2026, 8, 2),
            end_date=date(2026, 8, 1),
            intro="Úvod",
            body="Text",
        )
        with self.assertRaises(ValidationError):
            invalid_trip.full_clean()
