from datetime import date
from django import forms
from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from modelcluster.contrib.taggit import ClusterTaggableManager
from taggit.models import TaggedItemBase
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.images.models import Image
from wagtail.search import index
from django.utils import timezone
from wagtail.snippets.models import register_snippet


class BlogIndexPage(Page):
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
    
    # add the get_context method:
    def get_context(self, request):
        # Update context to include only published posts, ordered by reverse-chron
        context = super().get_context(request)
        blogpages = self.get_children().live().order_by('-first_published_at')
        context['blogpages'] = blogpages
        return context

    content_panels = Page.content_panels + [
        FieldPanel("image"),
        FieldPanel('intro'),
    ]

    parent_page_types = ["home.HomePage"]
    subpage_types = ['BlogPage']

    
class BlogTagIndexPage(Page):
    max_count = 1

    def get_context(self, request):

        # Filter by tag
        tag = request.GET.get('tag')
        blogpages = BlogPage.objects.filter(tags__name=tag)

        # Update template context
        context = super().get_context(request)
        context['blogpages'] = blogpages
        return context  


class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'BlogPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )


class BlogPage(Page):
    blog_nr = models.PositiveIntegerField("Číslo blogu", unique=True, null=True)
    date = models.DateField("Datum publikace", default=date.today)
    intro = models.CharField("Úvod", max_length=250)
    body = RichTextField("Tělo blogu")
    authors = ParentalManyToManyField('blog.Author', blank=True, verbose_name='Autor')
    tags = ClusterTaggableManager(through=BlogPageTag, blank=True)

    # Add the main_image method:
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
        FieldPanel('intro'),
        FieldPanel('body'),
        InlinePanel('gallery_images', label="Galerie obrázků"),        
    ]
        
    parent_page_types = ['BlogIndexPage']

    def get_context(self, request):
        context = super().get_context(request)

        # Fetch the parent BlogIndexPage
        blog_index = self.get_parent().specific
        context['blog_index'] = blog_index
        return context

    def save(self, *args, **kwargs):
        if self.pk is None:  # Jen pokud se jedná o nový objekt
            last_blog = BlogPage.objects.order_by('blog_nr').last()
            self.blog_nr = last_blog.blog_nr + 1 if last_blog else 1
        super().save(*args, **kwargs)

    
class BlogPageGalleryImage(Orderable):
    page = ParentalKey(BlogPage, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ForeignKey(
        'wagtailimages.Image', on_delete=models.CASCADE, related_name='+'
    )
    caption = models.CharField(blank=True, max_length=250)

    panels = [
        FieldPanel('image'),
        FieldPanel('caption'),
    ]


@register_snippet
class Author(models.Model):
    name = models.CharField(max_length=255)
    author_image = models.ForeignKey(
        'wagtailimages.Image', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+'
    )

    panels = [
        FieldPanel('name'),
        FieldPanel('author_image'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Autoři'
        
