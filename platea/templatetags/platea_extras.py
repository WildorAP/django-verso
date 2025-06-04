from django import template

register = template.Library()

@register.filter
def split(value, delimiter='_'):
    """
    Divide una cadena usando el delimitador especificado.
    Uso: {{ value|split:'_' }}
    """
    return value.split(delimiter) 