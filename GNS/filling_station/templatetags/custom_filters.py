from django import template

register = template.Library()

@register.filter
def float_format(value):
    if value is None:
        return "-"
    return f"{float(value):.2f}"

@register.simple_tag
def get_post_correction(settings, post_num):
    """
    Для отображения корректоров карусели
    """
    return getattr(settings, f'post_{post_num}_correction', 0.0)
