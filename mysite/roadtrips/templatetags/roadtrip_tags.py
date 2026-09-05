from django import template

register = template.Library()


@register.inclusion_tag("blocks/road_trip_route.html")
def road_trip_route(value):
    """Insert home icons while keeping the surrounding route as escaped text."""
    return {"parts": (value or "").split(":home:")}
