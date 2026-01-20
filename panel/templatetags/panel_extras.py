from django import template
register = template.Library()

@register.filter
def get_item(d, key):
    if not d:
        return None
    try:
        return d.get(key)
    except Exception:
        return None
