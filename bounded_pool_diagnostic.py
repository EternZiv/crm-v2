"""External deadline; owns and cleans up only the diagnostic child."""
import subprocess
import sys
from pathlib import Path

command=[sys.executable,'-u','pool_asgi_evaluation.py','authenticated','diagnostic',*sys.argv[1:]]
prefix='pool_diagnostic_'+('_'.join(sys.argv[1:]) or 'dashboard')
with open(prefix+'_stdout.log','w',encoding='utf-8') as stdout, open(prefix+'_stderr.log','w',encoding='utf-8') as stderr:
    child=subprocess.Popen(command,stdout=stdout,stderr=stderr)
    try:
        code=child.wait(timeout=50)
        print('EXIT',code)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)
        print('EXTERNAL_TIMEOUT',child.pid)
for filename in [prefix+'_stdout.log',prefix+'_stderr.log']:
    print(filename)
    print(Path(filename).read_text(encoding='utf-8')[-18000:])
