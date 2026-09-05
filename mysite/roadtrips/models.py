from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm

from .blocks import RoadTripDayContentBlock, RoadTripOverviewContentBlock


class RoadTripDayPageForm(WagtailAdminPageForm):
    """Validuje nový den ještě před jeho vložením do stromu stránek."""

    def clean(self):
        cleaned_data = super().clean()
        road_trip = self.parent_page.specific if self.parent_page else None
        day_number = cleaned_data.get("day_number")
        day_date = cleaned_data.get("date")

        if road_trip and day_date:
            if not road_trip.start_date <= day_date <= road_trip.end_date:
                self.add_error(
                    "date", "Datum dne musí spadat do termínu celé cesty."
                )

        if road_trip and day_number is not None:
            duplicate_day = (
                RoadTripDayPage.objects.child_of(road_trip)
                .filter(day_number=day_number)
                .exclude(pk=self.instance.pk)
                .exists()
            )
            if duplicate_day:
                self.add_error(
                    "day_number", "Toto číslo dne už cesta obsahuje."
                )

            content = cleaned_data.get("content")
            if content is not None:
                try:
                    RoadTripDayPage.validate_mileage(
                        road_trip, day_number, content, exclude_pk=self.instance.pk
                    )
                except ValidationError as error:
                    self.add_error("content", error)

        return cleaned_data


class RoadTripIndexPage(Page):
    """Rozcestník všech autovandrů."""

    max_count = 1

    subtitle = models.CharField(
        "Podtitulek v menu",
        max_length=20,
        default="Autovandry",
        help_text="Krátký název zobrazovaný v hlavním menu.",
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Titulní obrázek sekce, ideálně na šířku (1000 až 3000 px).",
    )
    intro = RichTextField("Úvod", blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("subtitle"),
        FieldPanel("image"),
        FieldPanel("intro"),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ["roadtrips.RoadTripPage"]

    class Meta:
        verbose_name = "Rozcestník autovandrů"

    def get_road_trips(self):
        return (
            RoadTripPage.objects.child_of(self)
            .live()
            .order_by("-start_date")
            .specific()
        )

    def get_context(self, request):
        context = super().get_context(request)
        context["road_trips"] = self.get_road_trips()
        return context


class RoadTripPage(Page):
    """Nadřazená stránka jedné cesty s jejím celkovým popisem."""

    start_date = models.DateField("Začátek cesty", default=date.today)
    end_date = models.DateField("Konec cesty", default=date.today)
    mapy_route_url = models.URLField(
        "Mapa trasy na Mapy.com",
        blank=True,
        help_text=(
            "Vložte pouze sdílecí URL mapy, například "
            "https://mapy.com/s/hodepofuza. Náhled se vytvoří automaticky."
        ),
    )
    intro = models.CharField("Krátký úvod", max_length=300)
    content = StreamField(
        RoadTripOverviewContentBlock(),
        blank=True,
        use_json_field=True,
        verbose_name="Řaditelný obsah",
        help_text=(
            "Libovolně střídejte texty, vlastní obrázky a vlastní videa. "
            "Přidat můžete také blok Přehled autovandru."
        ),
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Titulní obrázek cesty",
    )
    image_heading = models.CharField(
        "Nadpis titulní fotografie",
        max_length=150,
        blank=True,
        help_text="Volitelný nadpis zobrazený nad titulní fotografií.",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("start_date"), FieldPanel("end_date")],
            heading="Termín cesty",
        ),
        FieldPanel("mapy_route_url"),
        FieldPanel("intro"),
        FieldPanel("image"),
        FieldPanel("image_heading"),
        FieldPanel("content"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("content"),
    ]

    parent_page_types = ["roadtrips.RoadTripIndexPage"]
    subpage_types = ["roadtrips.RoadTripDayPage"]

    class Meta:
        verbose_name = "Autovandr"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "Konec cesty nesmí být před jejím začátkem."}
            )

    def get_days(self):
        return (
            RoadTripDayPage.objects.child_of(self)
            .live()
            .order_by("day_number", "date")
            .specific()
        )

    def get_road_trip_index(self):
        return self.get_parent().specific

    def get_trip_summary(self, days=None):
        days = list(self.get_days() if days is None else days)
        summary = {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "duration_days": None,
            "total_distance_km": None,
            "distance_day_number": None,
            "distance_is_partial": False,
            "countries": [],
            "seas": [],
        }
        if self.start_date and self.end_date and self.end_date >= self.start_date:
            summary["duration_days"] = (self.end_date - self.start_date).days + 1
        seen = {"countries": set(), "seas": set()}
        for day in days:
            total = day.get_total_distance_km()
            if total is not None:
                summary["total_distance_km"] = total
                summary["distance_day_number"] = day.day_number
                summary["distance_is_partial"] = day.date != self.end_date
            for block in day.content:
                if block.block_type != "day_summary":
                    continue
                for field in seen:
                    for place in block.value.get(field, []):
                        name = place.strip()
                        key = name.casefold()
                        if name and key not in seen[field]:
                            summary[field].append(name)
                            seen[field].add(key)
        if days and summary["distance_day_number"] is not None:
            summary["distance_is_partial"] = (
                summary["distance_is_partial"]
                or summary["distance_day_number"] != days[-1].day_number
            )
        return summary

    def get_context(self, request):
        context = super().get_context(request)
        context["days"] = list(self.get_days())
        context["trip_summary"] = self.get_trip_summary(context["days"])
        context["road_trip_index"] = self.get_road_trip_index()
        return context


class RoadTripDayPage(Page):
    """Blogový zápis jednoho dne konkrétního autovandru."""

    day_number = models.PositiveSmallIntegerField(
        "Číslo dne", validators=[MinValueValidator(1)]
    )
    date = models.DateField("Datum", default=date.today)
    mapy_route_url = models.URLField(
        "Mapa trasy na Mapy.com",
        blank=True,
        help_text=(
            "Vložte pouze sdílecí URL mapy, například "
            "https://mapy.com/s/hodepofuza. Náhled se vytvoří automaticky."
        ),
    )
    intro = models.CharField("Krátký úvod", max_length=300)
    content = StreamField(
        RoadTripDayContentBlock(),
        blank=True,
        use_json_field=True,
        verbose_name="Řaditelný obsah",
        help_text=(
            "Libovolně střídejte texty, vlastní obrázky a vlastní videa. "
            "Na konec zápisu můžete přidat blok Přehled dne."
        ),
    )
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="Titulní obrázek dne",
    )
    image_heading = models.CharField(
        "Nadpis titulní fotografie",
        max_length=150,
        blank=True,
        help_text="Volitelný nadpis zobrazený nad titulní fotografií.",
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("day_number"), FieldPanel("date")],
            heading="Den cesty",
        ),
        FieldPanel("mapy_route_url"),
        FieldPanel("intro"),
        FieldPanel("image"),
        FieldPanel("image_heading"),
        FieldPanel("content"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("intro"),
        index.SearchField("content"),
    ]

    parent_page_types = ["roadtrips.RoadTripPage"]
    subpage_types = []
    base_form_class = RoadTripDayPageForm

    class Meta:
        verbose_name = "Den autovandru"

    def main_image(self):
        return self.image

    def get_road_trip(self):
        return self.get_parent().specific

    def get_road_trip_index(self):
        return self.get_parent().get_parent().specific

    @staticmethod
    def total_distance_from_content(content):
        for block in content:
            if block.block_type == "day_summary":
                return block.value.get("total_distance_km")
        return None

    def get_total_distance_km(self):
        return self.total_distance_from_content(self.content)

    def get_daily_distance_km(self, total, *, is_preview=False):
        if total is None:
            return None
        if self.day_number == 1:
            return total
        if not self.path:
            return None

        # Use the immediately preceding day, not the previous available total:
        # a missing day must not turn several days' mileage into one day's.
        previous_days = RoadTripDayPage.objects.child_of(self.get_road_trip()).filter(
            day_number=self.day_number - 1
        )
        if not is_preview:
            previous_days = previous_days.live()
        previous_day = previous_days.first()
        if previous_day is None:
            return None
        if is_preview:
            previous_day = previous_day.get_latest_revision_as_object()
        previous_total = previous_day.get_total_distance_km()
        if previous_total is None or total < previous_total:
            return None
        return total - previous_total

    @classmethod
    def validate_mileage(cls, road_trip, day_number, content, *, exclude_pk=None):
        total = cls.total_distance_from_content(content)
        if total is None or day_number is None:
            return
        neighbours = cls.objects.child_of(road_trip).filter(
            day_number__in=[day_number - 1, day_number + 1]
        ).exclude(pk=exclude_pk)
        for neighbour in neighbours:
            neighbour = neighbour.get_latest_revision_as_object()
            neighbour_total = neighbour.get_total_distance_km()
            if neighbour_total is None:
                continue
            if neighbour.day_number < day_number and total < neighbour_total:
                raise ValidationError(
                    "Celkové kilometry nesmí být menší než u předchozího dne."
                )
            if neighbour.day_number > day_number and total > neighbour_total:
                raise ValidationError(
                    "Celkové kilometry nesmí být větší než u následujícího dne."
                )

    def clean(self):
        super().clean()
        if not self.path:
            return

        road_trip = self.get_road_trip()
        errors = {}
        if self.date and not road_trip.start_date <= self.date <= road_trip.end_date:
            errors["date"] = "Datum dne musí spadat do termínu celé cesty."

        duplicate_day = (
            RoadTripDayPage.objects.child_of(road_trip)
            .filter(day_number=self.day_number)
            .exclude(pk=self.pk)
            .exists()
        )
        if duplicate_day:
            errors["day_number"] = "Toto číslo dne už cesta obsahuje."

        try:
            self.validate_mileage(
                road_trip, self.day_number, self.content, exclude_pk=self.pk
            )
        except ValidationError as error:
            errors["content"] = error.messages

        if errors:
            raise ValidationError(errors)

    def get_context(self, request):
        context = super().get_context(request)
        road_trip = self.get_road_trip()
        days = list(road_trip.get_days())

        previous_day = next_day = None
        if self in days:
            current_index = days.index(self)
            if current_index > 0:
                previous_day = days[current_index - 1]
            if current_index < len(days) - 1:
                next_day = days[current_index + 1]

        context.update(
            {
                "road_trip": road_trip,
                "road_trip_index": self.get_road_trip_index(),
                "previous_day": previous_day,
                "next_day": next_day,
            }
        )
        return context
