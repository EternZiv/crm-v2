import os, sys, django
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finlo.settings')
django.setup()
from django.template import Template, Context

tpl = Template("""{% spaceless %}
<tr>
    <td
        class="
            bg-white
            text-sm
        "
    >
        <span>  hello  </span>
    </td>
</tr>
{% endspaceless %}""")

out = tpl.render(Context({}))
print("Output:\n", out)

