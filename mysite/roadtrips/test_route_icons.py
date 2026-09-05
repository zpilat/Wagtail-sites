from django.template import Context, Template
from django.test import SimpleTestCase

from .blocks import RoadTripDaySummaryBlock, RoadTripSummaryBlock


class RouteIconTests(SimpleTestCase):
    def render_route(self, route):
        return Template("{% load roadtrip_tags %}{% road_trip_route route %}").render(
            Context({"route": route})
        )

    def test_home_markers_render_as_icons_in_route_order(self):
        html = self.render_route(":home: → Oslo → :home:")
        self.assertEqual(html.count('class="fa-solid fa-house"'), 2)
        self.assertEqual(html.count('class="visually-hidden">Domov</span>'), 2)
        self.assertNotIn(":home:", html)
        self.assertLess(html.index("fa-house"), html.index("Oslo"))
        self.assertLess(html.index("Oslo"), html.rindex("fa-house"))

    def test_routes_without_markers_are_preserved(self):
        self.assertEqual(self.render_route("Praha → Oslo").strip(), "Praha → Oslo")
        self.assertEqual(self.render_route("").strip(), "")
        self.assertEqual(self.render_route(None).strip(), "")

    def test_route_text_remains_escaped(self):
        html = self.render_route("<script>alert(1)</script> → :home: & Oslo")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("&amp; Oslo", html)
        self.assertIn('class="fa-solid fa-house"', html)

    def test_icons_render_in_both_summary_blocks_only_in_route(self):
        for block in (RoadTripDaySummaryBlock(), RoadTripSummaryBlock()):
            with self.subTest(block=type(block).__name__):
                html = block.render(
                    block.to_python(
                        {
                            "heading": "Přehled",
                            "route": ":home: → Oslo",
                            "note": "Poznámka :home:",
                        }
                    )
                )
                self.assertEqual(html.count('class="fa-solid fa-house"'), 1)
                self.assertIn("Poznámka :home:", html)
