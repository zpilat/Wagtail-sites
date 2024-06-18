from django.db import models
from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel

from cookbook.blocks import CookbookStreamBlock


class CookbookIndexPage(Page):
    max_count = 1

    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Landscape mode only; horizontal width between 1000px and 3000px.",
    )
    intro = RichTextField(blank=True)
    
    def get_context(self, request):
        context = super().get_context(request)
        cookbookpages = self.get_children().live().order_by('-first_published_at')
        context['cookbookpages'] = cookbookpages
        return context

    content_panels = Page.content_panels + [
        FieldPanel("image"),
        FieldPanel('intro'),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ['CookbookPage']


class CookbookPage(Page):
    parent_page_types = ['CookbookIndexPage']

    blog_nr = models.PositiveIntegerField("Číslo blogu", unique=True, null=True)
    body = StreamField(
        CookbookStreamBlock(),
        blank=True,
        use_json_field=True,
        help_text="Zde zadej recept:",
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]
    
    def save(self, *args, **kwargs):
        if self.pk is None:  # Jen pokud se jedná o nový objekt
            last_blog = BlogPage.objects.order_by('blog_nr').last()
            self.blog_nr = last_blog.blog_nr + 1 if last_blog else 1
        super().save(*args, **kwargs)
