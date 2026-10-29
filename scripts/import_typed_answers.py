"""Explicit one-time import of cached structured answers into editable sources."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import tempfile

from bs4 import NavigableString

from scripts.build_collected_papers import Converter
from scripts.build_papers import ROOT


def latex(tag):
    """Preserve the source's explicit formula structure as editable TeX."""
    if isinstance(tag, NavigableString):
        value = str(tag)
        for old, new in {'×': r'\times ', '·': r'\cdot ', '≤': r'\le ',
                         '≥': r'\ge ', '−': '-', '∞': r'\infty '}.items():
            value = value.replace(old, new)
        value = value.replace('%', r'\%')
        return re.sub(r'[\u3400-\u9fff]+', lambda m: r'\text{' + m[0] + '}', value)
    classes = tag.get('class', [])
    if 'markdown-math-fraction' in classes:
        return r'\frac{' + latex(tag.select_one('.markdown-math-numerator')) + '}{' + latex(tag.select_one('.markdown-math-denominator')) + '}'
    body = ''.join(latex(child) for child in tag.children)
    if tag.name == 'sup': return '^{' + body + '}'
    if tag.name == 'sub': return '_{' + body + '}'
    if 'markdown-math-overline' in classes: return r'\overline{' + body + '}'
    return body


class AnswerConverter(Converter):
    def node(self, tag):
        if not isinstance(tag, NavigableString) and 'markdown-math-inline' in tag.get('class', []):
            self.counts['formulas'] += 1
            return {'kind': 'math', 'value': latex(tag)}
        return super().node(tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', nargs='+', type=int, required=True)
    args = parser.parse_args()
    dataset = ROOT / 'resources/beokayy'
    reviews = json.loads((ROOT / 'typst/archive/scan-edition-2026-10-29/scan-reviews.json').read_text())
    for year in args.years:
        output = ROOT / f'typst/answers/{year}.json'
        if output.exists():
            raise ValueError(f'Preserve edited answers: {output}')
        source = dataset / f'papers/{year}.json'
        data = json.loads(source.read_text())
        answers = []
        with tempfile.TemporaryDirectory() as folder:
            converter = AnswerConverter(dataset, Path(folder))
            def clean(nodes):
                result = []
                for n in nodes:
                    n = dict(n)
                    if n['kind'] == 'text':
                        n['value'] = re.sub(r'【(?:参考答案|答案|解析)】', '', n['value']).replace('\\,','\u2009')
                        if n['value'].strip() in ('答案：', '答案:', '答案'):
                            continue
                    if n['kind'] == 'image':
                        original = Path(folder) / n['path']
                        target = ROOT / f'typst/assets/answers/{year}' / original.name
                        target.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(original,target)
                        n['path']=target.relative_to(ROOT/'typst').as_posix()
                        n['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
                    for key in ('children','top','bottom'):
                        if key in n:n[key]=clean(n[key])
                    if 'cells' in n:
                        for cell in n['cells']:cell['children']=clean(cell['children'])
                    if 'rows' in n:n['rows']=[[clean(c) for c in row] for row in n['rows']]
                    if 'items' in n:n['items']=[clean(i) for i in n['items']]
                    result.append(n)
                return result
            for q in data['questions']:
                n=q['number'];nodes=[] if n<=40 else clean(converter.content(q['answer']['html']))
                correction=ROOT/f'typst/answers/corrections/{year}-{n}.md'
                if correction.exists():
                    nodes=[{'kind':'include','path':correction.relative_to(ROOT/'typst').as_posix()}]
                answers.append({'number':n,'choice':q['answer_choice'] if n<=40 else None,'nodes':nodes})
        assert ''.join(a['choice'] for a in answers[:40])==reviews[str(year)]['choice_key']
        result={'year':str(year),'source_url':data['url'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'paper_sha256':hashlib.sha256((ROOT/f'typst/papers/{year}.md').read_bytes()).hexdigest(),
                'choice_explanations':f'answers/choices/{year}.md','answers':answers}
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(year,dict(converter.counts))

if __name__=='__main__':main()
