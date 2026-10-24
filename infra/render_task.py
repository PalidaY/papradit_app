"""Render non-secret ECS metadata; secret values are never read by this renderer."""
import json,os,re,sys
from pathlib import Path
text=Path(__file__).with_name('ecs-task.json').read_text()
keys=set(re.findall(r'\$\{([A-Z_]+)\}',text))
missing=sorted(k for k in keys if not os.environ.get(k))
if missing: raise SystemExit('Missing configuration names: '+', '.join(missing))
# JSON-escape every substituted string fragment.
result=re.sub(r'\$\{([A-Z_]+)\}',lambda m:json.dumps(os.environ[m[1]])[1:-1],text)
json.dump(json.loads(result),sys.stdout,indent=2)
