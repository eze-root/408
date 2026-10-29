"""Load editable structured answers and their independently reviewed explanations."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def markdown_nodes(value):
    """Separate prose paragraphs without splitting blank lines inside code."""
    nodes, lines, language = [], [], None
    def prose():
        if lines:
            nodes.extend({'kind': 'markdown', 'value': p.strip()}
                         for p in re.split(r'\n\s*\n', '\n'.join(lines)) if p.strip())
            lines.clear()
    for line in value.splitlines():
        if line.startswith('```'):
            if language is None:
                prose()
                language = line[3:].strip() or 'text'
            else:
                nodes.append({'kind': 'code', 'block': True, 'lang': language,
                              'value': '\n'.join(lines)})
                lines.clear()
                language = None
        else:
            lines.append(line)
    if language is not None:
        raise ValueError('Unclosed answer code fence')
    prose()
    return nodes


def walk(nodes):
    for node in nodes:
        yield node
        for key in ('children','top','bottom'):
            yield from walk(node.get(key,[]))
        for item in node.get('items',[]):yield from walk(item)
        for row in node.get('rows',[]):
            for cell in row:yield from walk(cell)
        for cell in node.get('cells',[]):yield from walk(cell['children'])


def load_typed(year):
    path=ROOT/f'typst/answers/{year}.json'
    if not path.exists():return None
    source=json.loads(path.read_text())
    if hashlib.sha256((ROOT/f'typst/papers/{year}.md').read_bytes()).hexdigest()!=source['paper_sha256']:
        raise ValueError(f'{year}: review answer pairing after question edits')
    choices=(ROOT/'typst'/source['choice_explanations']).read_text()
    matches=list(re.finditer(r'^## (\d+)\.\s*$',choices,re.M))
    if [int(m[1]) for m in matches]!=list(range(1,41)):
        raise ValueError(f'{year}: expected 40 choice explanations')
    answers=source['answers']
    if [a['number'] for a in answers]!=list(range(1,48)):
        raise ValueError(f'{year}: expected 47 answers')
    for i,a in enumerate(answers):
        a.update(body='',options=[])
        if i<40:
            end=matches[i+1].start() if i<39 else len(choices)
            body=choices[matches[i].end():end].strip()
            if len(body)<12 or not re.fullmatch('[ABCD]', a['choice'] or ''):
                raise ValueError(f'{year} Q{i+1}: incomplete choice answer')
            a['nodes']=markdown_nodes(body)
        expanded = []
        for node in a['nodes']:
            if node['kind'] == 'include':
                included = (ROOT/'typst'/node['path']).resolve()
                if not included.is_relative_to(ROOT/'typst/answers'):
                    raise ValueError('Answer include must be inside typst/answers')
                body = re.sub(r'^##[^\n]+\n+', '', included.read_text())
                expanded.extend(markdown_nodes(body))
            elif node['kind'] == 'markdown':
                expanded.extend(markdown_nodes(node['value']))
            else:
                expanded.append(node)
        a['nodes'] = expanded
        if not a['nodes']:raise ValueError(f'{year} Q{i+1}: missing solution')
        for n in walk(a['nodes']):
            if n['kind']=='image':
                asset=(ROOT/'typst'/n['path']).resolve()
                if not asset.is_relative_to(ROOT/'typst/assets/answers'):
                    raise ValueError(f'{year}: nonportable answer figure')
                if hashlib.sha256(asset.read_bytes()).hexdigest()!=n['sha256']:
                    raise ValueError(f'{year}: changed answer figure {asset}')
    return answers
