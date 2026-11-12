"""Syntax screening only; Django substitutions can produce false positives."""
import json
import os
from pathlib import Path
import re
import subprocess
from html.parser import HTMLParser

os.environ['DJANGO_SETTINGS_MODULE'] = 'finlo.settings.security_test'
import django
django.setup()
from django.template import engines
from django.template.utils import get_app_template_dirs

class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []
        self.scripts = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script':
            self.active = 'src' not in attrs and attrs.get('type', 'text/javascript') in ('text/javascript', 'application/javascript', 'module', '')
            self.parts = []
    def handle_data(self, text):
        if self.active: self.parts.append(text)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            self.scripts.append(''.join(self.parts))
            self.active = False

count = 0
errors = []
for root in list(engines['django'].engine.dirs) + list(get_app_template_dirs('templates')):
    if '.venv' in str(root): continue
    for file in Path(root).rglob('*.html'):
        parser = Scripts()
        parser.feed(file.read_text(encoding='utf-8-sig'))
        for i, script in enumerate(parser.scripts):
            if not script.strip(): continue
            count += 1
            script = re.sub(r'{%.*?%}', '', script, flags=re.S)
            script = re.sub(r'{{.*?}}', '0', script, flags=re.S)
            result = subprocess.run(['node', '--check'], input=script, text=True, encoding='utf-8', capture_output=True, timeout=6)
            if result.returncode:
                errors.append({'file': str(file.relative_to(Path.cwd())), 'script': i, 'diagnostic': result.stderr[:1000]})
result = {'checked': count, 'candidates': errors}
Path('FINLO_INLINE_SCRIPT_RESULTS.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
