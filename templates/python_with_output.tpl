{%- extends 'python/index.py.j2' -%}

{% block codecell %}
{{ super() }}
{%- for out in cell.outputs %}
# ── Cell Output ──
{%- if out.output_type == 'stream' and out.text %}
{%- for line in out.text.splitlines() %}
# {{ line }}
{%- endfor %}
{%- elif out.output_type in ['execute_result','display_data'] %}
{# only grab text/plain if it exists #}
{%- set txt = out.data.get('text/plain','') %}
{%- if txt %}
{%- for line in txt.splitlines() %}
# {{ line }}
{%- endfor %}
{%- endif %}
{%- endif %}
{%- endfor %}
{% endblock codecell %}

