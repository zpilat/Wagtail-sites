from wagtail import hooks
from wagtail.images.formats import Format, register_image_format, unregister_image_format
from .models import BlogPage 
import re

@hooks.register('register_rich_text_features')
def register_custom_image_format(features):
    unregister_image_format('fullwidth')
    register_image_format(Format('fullwidth', 'Full width', 'richtext-image full-width', 'width-1024'))


