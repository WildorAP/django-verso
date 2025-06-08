from django import template

register = template.Library()

@register.filter
def split(value, delimiter='_'):
    """
    Divide una cadena usando el delimitador especificado.
    
    Args:
        value: La cadena a dividir
        delimiter: El delimitador a usar (por defecto '_')
    
    Returns:
        Lista de subcadenas
    
    Uso en template:
        {{ value|split:'_' }}
    """
    return value.split(delimiter) 