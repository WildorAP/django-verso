from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    args = arg.split(' to ')
    if len(args) != 2:
        return value
    return value.replace(args[0], args[1])

@register.filter
def split(value, arg):
    return value.split(arg)