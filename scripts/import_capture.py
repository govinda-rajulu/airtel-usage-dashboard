#!/usr/bin/env python3
"""Import reviewed Airtel capture values into docs/data/usage.json.
Never import request headers, cookies, or tokens."""
import json,sys
from pathlib import Path
if len(sys.argv)!=2:
    raise SystemExit('Usage: python3 scripts/import_capture.py <capture.json>')
repo=Path(__file__).resolve().parents[1]
target=repo/'docs'/'data'/'usage.json'
source=Path(sys.argv[1]).resolve()
if not source.is_file() or source.suffix.lower()!='.json':
    raise SystemExit('Refusing: input must be one existing JSON capture')
data=json.loads(source.read_text())
current=json.loads(target.read_text())
def mask_all(x):
    if isinstance(x,dict):return {k:mask_all(v) for k,v in x.items()}
    if isinstance(x,list):return [mask_all(v) for v in x]
    if isinstance(x,str):
        import re
        x=re.sub(r'(\d{2})\d{4,}(\d{2})',r'\1***\2',x)
        x=re.sub(r'(^[^@\s]{3})[^@\s]*(@.*)',r'\1***\2',x)
    return x
data=mask_all(data)
page=str(data.get('pageText') or data.get('text') or '')
if not page and not data.get('responses'):
    raise SystemExit('Refusing: capture has neither page text nor responses')
changed=[]
def set_if(section,key,value):
    if value and current.get(section,{}).get(key)!=value:
        current.setdefault(section,{})[key]=value;changed.append(f'{section}.{key}')
# Conservative imports: only fields already verified in owner captures.
if 'Airtel Black' in page: set_if('plan','name','Airtel Black')
for line in page.splitlines():
    if line.startswith('₹') and 'Plan' in line and current.get('connections'):
        current['connections'][0]['plan']=line;changed.append('connections[0].plan')
    if line=='30 Mbps' and current.get('connections') and current['connections'][0].get('speed')!=line:
        current['connections'][0]['speed']=line;changed.append('connections[0].speed')
current['fetchLog'].insert(0,{'at':str(data.get('capturedAt','unknown')),'result':'Capture import','detail':f'Imported reviewed visible details from {source.name}; usage figures were imported only when explicitly present.'})
target.write_text(json.dumps(current,indent=2,ensure_ascii=False)+'\n')
print('IMPORTED',source.name)
print('CHANGED',', '.join(changed) if changed else 'none')
print('WROTE',target)
