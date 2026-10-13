"""Read-only exact DOCX title transcription check; does not validate OCR truth."""
import difflib
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
def norm(text):
    return re.sub(r'\s+', '', text)

def verify_ref(ref):
    p = Path(ref['path'])
    if not p.is_absolute() or str(p).startswith(('\\\\', '//')):
        raise ValueError('需要本地绝对路径')
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    if h.hexdigest() != ref['sha256']:
        raise ValueError('指纹变化: ' + str(p))

def check(data):
    verify_ref(data['artifact'])
    ids = data['expected_ids']
    items = data['items']
    got = [i['id'] for i in items]
    if not ids or len(ids) != len(set(ids)) or len(got) != len(set(got)) or set(got) != set(ids):
        raise ValueError('标题清单范围缺失或重复')
    indices = [i['paragraph_index'] for i in items]
    if len(indices) != len(set(indices)):
        raise ValueError('多个标题指向同一段落')
    with zipfile.ZipFile(data['artifact']['path']) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    paras = root.findall('.//w:p', NS)
    results = []
    for item in items:
        if not re.fullmatch(r'\d+(?:-\d+)+', item['id']):
            raise ValueError('附件编号格式错误')
        if item.get('source_reviewed') is not True or not item.get('review_note') or not item.get('source_locator'):
            raise ValueError('原件标题尚未核实')
        verify_ref(item['source_evidence'])
        expected = norm(item['source_title'])
        if not expected:
            raise ValueError('原件标题为空')
        idx = item['paragraph_index']
        if type(idx) is not int or not 0 <= idx < len(paras):
            raise ValueError('输出段落定位失效')
        para = paras[idx]
        if any(para.find('.//w:' + tag, NS) is not None for tag in ('del', 'ins', 'vanish', 'webHidden', 'fldChar', 'fldSimple', 'txbxContent', 'sym', 'drawing', 'pict', 'pPrChange', 'rPrChange', 'moveFrom', 'moveTo')):
            raise ValueError('复杂或非普通可见文字段落，须专项核验')
        raw_text = ''.join(t.text or '' for t in para.findall('.//w:t', NS)).strip()
        match = re.match(r'^附件\s*(\d+(?:\s*-\s*\d+)+)\s*(.*)$', raw_text, re.S)
        if not match or norm(match.group(1)) != item['id']:
            raise ValueError('段落附件编号不匹配')
        actual = norm(match.group(2))
        delta = [{'operation': tag, 'source': expected[a:b], 'output': actual[c:d]}
                 for tag, a, b, c, d in difflib.SequenceMatcher(a=expected, b=actual, autojunk=False).get_opcodes() if tag != 'equal']
        results.append({'id': item['id'], 'matches': not delta, 'expected': item['source_title'], 'actual': actual, 'delta': delta})
    # Recheck after reading: do not report a stale output snapshot as the current file.
    verify_ref(data['artifact'])
    return {'status': 'transcription_matches' if all(r['matches'] for r in results) else 'title_changes_required',
            'checked': len(results), 'items': results,
            'limitation': 'Only exact text for declared scope; source OCR/visual truth, scope completeness and layout are not proven.'}

if __name__ == '__main__':
    try:
        result = check(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result['status'] == 'transcription_matches' else 2)
    except (ValueError, KeyError, OSError, IndexError, ET.ParseError, zipfile.BadZipFile) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        sys.exit(2)
