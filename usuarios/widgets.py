from django.forms.widgets import ClearableFileInput
from django.utils.safestring import mark_safe

class ArchivoConstanciaWidget(ClearableFileInput):
    def render(self, name, value, attrs=None, renderer=None):
        html = ""
        if value and hasattr(value, "url"):
            html += f"""
                <div style="margin-bottom: 10px;">
                    <a href="{value.url}" target="_blank" rel="noopener noreferrer">
                        📎 Ver constancia 
                    </a>
                </div>
            """
        input_html = super().render(name, value, attrs, renderer)
        return mark_safe(html + input_html)