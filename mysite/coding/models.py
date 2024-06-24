from datetime import date
from django import forms
from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import Tag, TaggedItemBase
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.images.models import Image
from wagtail.search import index
from django.utils import timezone
from wagtail.snippets.models import register_snippet

class CodingPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'CodingPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class CodingIndexPage(Page):
    max_count = 1
    
    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Pouze režim na šířku; šířka mezi 1000px a 3000px.",
    ) 
    intro = RichTextField(help_text="Úvodní text popisující stránku", blank=True)
    
    content_panels = Page.content_panels + [
        FieldPanel("image"),
        FieldPanel('intro'),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ['CodingPage']

    def get_blogpages(self, tag=None):
        blogpages = BlogPage.objects.descendant_of(self).live().order_by('-first_published_at')
        if tag:
            blogpages = blogpages.filter(tags__slug=tag)
        return blogpages

    def get_child_tags(self):
        tags = []
        for blogpage in self.get_blogpages():
            tags += blogpage.tags.all()
        tags = sorted(set(tags), key=lambda tag: tag.name)
        return tags    

    def get_context(self, request):
        context = super().get_context(request)
        tag = request.GET.get('tag')
            
        context['blogpages'] = self.get_blogpages(tag)
        context['tags'] = self.get_child_tags()
        return context

    
class CodingPage(Page):
    blog_nr = models.PositiveIntegerField("Číslo blogu", unique=True, null=True)
    date = models.DateField("Datum publikace", default=date.today)
    intro = models.CharField("Úvod", max_length=250)
    body = RichTextField("Tělo blogu")
    authors = ParentalManyToManyField('blog.Author', blank=True, verbose_name='Autor')
    tags = ClusterTaggableManager(through=CodingPageTag, blank=True)

    def main_image(self):
        gallery_item = self.gallery_images.first()
        if gallery_item:
            return gallery_item.image
        else:
            return None

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
    ]

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('date'),
            FieldPanel('authors', widget=forms.CheckboxSelectMultiple),
            FieldPanel('tags'),
        ], heading="Informace o blogu"),
        FieldPanel('intro', heading="Úvod"),
        FieldPanel('body', heading="Tělo blogu"),
        InlinePanel('gallery_images', label="Galerie obrázků"),        
    ]
        
    parent_page_types = ['CodingIndexPage']

    def get_context(self, request):
        context = super().get_context(request)
        coding_index = self.get_parent().specific
        context['coding_index'] = coding_index
        return context

    def save(self, *args, **kwargs):
        if self.pk is None:  # Jen pokud se jedná o nový objekt
            last_blog = CodingPage.objects.order_by('blog_nr').last()
            self.blog_nr = last_blog.blog_nr + 1 if last_blog else 1
        super().save(*args, **kwargs)

    
class CodingPageGalleryImage(Orderable):
    page = ParentalKey(CodingPage, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ForeignKey(
        'wagtailimages.Image', on_delete=models.CASCADE, related_name='+'
    )
    caption = models.CharField(blank=True, max_length=250)

    panels = [
        FieldPanel('image'),
        FieldPanel('caption'),
    ]
