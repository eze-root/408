"""Compile the algorithms printed in the answer books and compare with brute force."""
import itertools
from scripts.typed_answers import load_typed, walk
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def code(year):
    source = (ROOT / f'typst/answers/{year}.md').read_text()
    return re.search(r'```c\n(.*?)\n```', source, re.S)[1]


@unittest.skipUnless(shutil.which('cc'), 'C compiler required for printed algorithm checks')
class PrintedAlgorithmTests(unittest.TestCase):
    def compile_and_run(self, source, data):
        with tempfile.TemporaryDirectory() as folder:
            cfile = Path(folder) / 'answer.c'
            binary = Path(folder) / 'answer'
            cfile.write_text(source)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=undefined', str(cfile), '-o', str(binary)],
                           check=True, capture_output=True, text=True)
            run = subprocess.run([str(binary)], input=data, capture_output=True,
                                 text=True, check=True)
            self.assertEqual(run.stderr, '')
            return run.stdout

    def test_2025_suffix_products_against_all_pairs(self):
        cases = [list(a) for n in range(1, 6) for a in itertools.product((-3, 0, 2), repeat=n)]
        cases.append([1, 4, -9, 6])
        source = '#include <stdio.h>\n' + code(2025) + '''
int main(void) {
    int n, a[16], result[16];
    while (scanf("%d", &n) == 1) {
        for (int i = 0; i < n; ++i) if (scanf("%d", &a[i]) != 1) return 1;
        calMulMax(a, result, n);
        for (int i = 0; i < n; ++i) printf("%d ", result[i]);
        puts("");
    }
    return 0;
}
'''
        result = self.compile_and_run(source, ''.join(f"{len(a)} {' '.join(map(str, a))}\n" for a in cases))
        got = [list(map(int, line.split())) for line in result.splitlines()]
        expected = [[max(x * y for y in a[i:]) for i, x in enumerate(a)] for a in cases]
        self.assertEqual(got, expected)

    def test_2026_nearest_bst_nodes_and_int_boundaries(self):
        rng = random.Random(408)
        cases = [([-2147483648], 2147483647), ([2147483647], -2147483648),
                 ([-2147483648, 2147483647], 0), ([2, 4], 3), ([3], 3)]
        for _ in range(150):
            cases.append((rng.sample(range(-100, 101), rng.randrange(1, 20)), rng.randrange(-120, 121)))
        source = '''#include <stdlib.h>
typedef struct BSTNode { int data; struct BSTNode *left, *right; } BinTNode;
typedef BinTNode *BTree;
''' + code(2026) + '''
int main(void) {
    int n, k; BinTNode nodes[32];
    while (scanf("%d%d", &n, &k) == 2) {
        BTree root = NULL;
        for (int i = 0; i < n; ++i) {
            if (scanf("%d", &nodes[i].data) != 1) return 1;
            nodes[i].left = nodes[i].right = NULL;
            BTree *link = &root;
            while (*link) link = nodes[i].data < (*link)->data ? &(*link)->left : &(*link)->right;
            *link = &nodes[i];
        }
        puts("CASE"); searchX(root, k);
    }
    return 0;
}
'''
        data = ''.join(f"{len(a)} {k} {' '.join(map(str, a))}\n" for a, k in cases)
        chunks = self.compile_and_run(source, data).split('CASE\n')[1:]
        self.assertEqual(len(chunks), len(cases))
        for chunk, (a, k) in zip(chunks, cases):
            values = [int(line.split('=')[1]) for line in chunk.splitlines()]
            distance = min(abs(x - k) for x in a)
            self.assertEqual(values[0], distance)
            self.assertEqual(set(values[1:]), {x for x in a if abs(x - k) == distance})

    def test_2023_k_vertices_all_four_vertex_digraphs(self):
        question = (ROOT / 'typst/papers/2023.md').read_text().split('## 41.')[1].split('## 42.')[0]
        structure = re.search(r'```c\n(.*?)\n```', question, re.S)[1]
        answer = (ROOT / 'typst/answers/corrections/2023-41.md').read_text()
        algorithm = re.search(r'```c\n(.*?)\n```', answer, re.S)[1]
        source = '#include <stdio.h>\n#define MAXV 4\n' + structure + '\n' + algorithm + '''
int main(void) {
    for (unsigned mask = 0; mask < 65536; ++mask) {
        MGraph G = {0}; G.numVertices = 4;
        for (int v = 0; v < 4; ++v) {
            G.VerticesList[v] = 'a' + v;
            for (int u = 0; u < 4; ++u)
                G.Edge[v][u] = (mask >> (v * 4 + u)) & 1;
        }
        int count = printVertices(G);
        printf("%d\\n", count);
    }
    return 0;
}
'''
        output = self.compile_and_run(source, '').splitlines()
        self.assertEqual(len(output), 65536)
        for mask, line in enumerate(output):
            # Independent edge-list tally includes isolated nodes and loops.
            balance = [0] * 4
            for edge in range(16):
                if mask & (1 << edge):
                    tail, head = divmod(edge, 4)
                    balance[tail] += 1
                    balance[head] -= 1
            vertices = [chr(97 + v) for v, b in enumerate(balance) if b > 0]
            self.assertEqual(line.split(), vertices + [str(len(vertices))], mask)


    def native_code(self, year, number):
        return '\n'.join(n['value'] for n in walk(load_typed(str(year))[number-1]['nodes'])
                         if n['kind'] == 'code' and n.get('block'))

    def test_2011_median_against_merged_arrays(self):
        cases = []
        for n in range(1, 5):
            arrays = list(itertools.combinations_with_replacement((-2, 0, 1, 4), n))
            cases.extend(itertools.product(arrays, repeat=2))
        source = '#include <stdio.h>\n' + self.native_code(2011, 42) + r'''
int main(void) {
    int n, a[8], b[8];
    while (scanf("%d", &n) == 1) {
        for (int i=0; i<n; ++i) if (scanf("%d", &a[i]) != 1) return 1;
        for (int i=0; i<n; ++i) if (scanf("%d", &b[i]) != 1) return 1;
        printf("%d\n", M_Search(a,b,n));
    }
    return 0;
}
'''
        data = ''.join(f"{len(a)} {' '.join(map(str, a+b))}\n" for a,b in cases)
        actual = list(map(int, self.compile_and_run(source, data).split()))
        self.assertEqual(actual, [sorted(a+b)[len(a)-1] for a,b in cases])

    def test_2015_absolute_value_dedup_keeps_first_occurrence(self):
        cases = [a for n in range(1, 6) for a in itertools.product((-2,-1,0,1,2), repeat=n)]
        source = '#include <stdio.h>\n#include <stdlib.h>\n' + self.native_code(2015, 41) + r'''
int main(void) {
    int n;
    while (scanf("%d", &n) == 1) {
        NODE h = {0, NULL}; PNODE tail = &h;
        for (int i=0; i<n; ++i) {
            tail->link = malloc(sizeof(NODE)); tail = tail->link; tail->link = NULL;
            if (scanf("%d", &tail->data) != 1) return 1;
        }
        func(&h, 2);
        for (PNODE p = h.link; p;) {
            printf("%d ", p->data); PNODE next = p->link; free(p); p = next;
        }
        puts("");
    }
    return 0;
}
'''
        data = ''.join(f"{len(a)} {' '.join(map(str, a))}\n" for a in cases)
        expected = []
        for a in cases:
            first = {}
            for x in a: first.setdefault(abs(x), x)
            expected.append(list(first.values()))
        actual = [list(map(int,line.split())) for line in self.compile_and_run(source,data).splitlines()]
        self.assertEqual(actual, expected)

    def test_2016_partition_matches_best_balanced_subset(self):
        cases = [a for n in range(2, 7) for a in itertools.product((1,3,7), repeat=n)]
        source = '#include <stdio.h>\n' + self.native_code(2016, 43) + r'''
int main(void) {
    int n, a[16];
    while (scanf("%d", &n) == 1) {
        for (int i=0; i<n; ++i) if (scanf("%d", &a[i]) != 1) return 1;
        printf("%d\n", setPartition(a,n));
    }
    return 0;
}
'''
        data = ''.join(f"{len(a)} {' '.join(map(str,a))}\n" for a in cases)
        actual = list(map(int,self.compile_and_run(source,data).split()))
        expected = [max(abs(sum(a)-2*sum(part)) for part in itertools.combinations(a,len(a)//2)) for a in cases]
        self.assertEqual(actual,expected)

    def test_2020_three_arrays_matches_brute_force_and_int_limits(self):
        arrays = [a for n in range(1,4) for a in itertools.combinations_with_replacement((-2,0,3),n)]
        cases = list(itertools.product(arrays,repeat=3))
        cases.extend([((-2147483648,), (0,), (2147483647,)),
                      ((-2147483648,2147483647), (2147483647,), (-2147483648,))])
        source = '#include <stdio.h>\n' + self.native_code(2020,41) + r'''
int main(void) {
    int n,m,p,a[8],b[8],c[8];
    while (scanf("%d%d%d",&n,&m,&p)==3) {
        for (int i=0;i<n;++i) if(scanf("%d",&a[i])!=1) return 1;
        for (int i=0;i<m;++i) if(scanf("%d",&b[i])!=1) return 1;
        for (int i=0;i<p;++i) if(scanf("%d",&c[i])!=1) return 1;
        printf("%lld\n",findMin(a,n,b,m,c,p));
    }
    return 0;
}
'''
        data = ''.join(f"{len(a)} {len(b)} {len(c)} {' '.join(map(str,a+b+c))}\n" for a,b,c in cases)
        actual = list(map(int,self.compile_and_run(source,data).split()))
        expected = [min(abs(x-y)+abs(y-z)+abs(z-x) for x,y,z in itertools.product(a,b,c)) for a,b,c in cases]
        self.assertEqual(actual,expected)

    def test_2022_bst_checks_entire_subtrees(self):
        cases = [a for a in itertools.product((-1,1,2,3), repeat=7)
                 if a[0]!=-1 and all(a[i]==-1 or a[(i-1)//2]!=-1 for i in range(1,7))]
        source = '#include <stdio.h>\n#include <stdlib.h>\n#include <stdbool.h>\n' + r'''
typedef struct { int SqBiTNode[16]; int ElemNum; } SqBiTree;
''' + self.native_code(2022,41) + r'''
int main(void) {
    SqBiTree b = {{0},7};
    while (scanf("%d",&b.SqBiTNode[0])==1) {
        for(int i=1;i<7;++i) if(scanf("%d",&b.SqBiTNode[i])!=1) return 1;
        printf("%d\n",judgeBST(b));
    }
    return 0;
}
'''
        def valid(a,i=0,lo=float('-inf'),hi=float('inf')):
            if i>=len(a) or a[i]==-1: return True
            return lo<a[i]<hi and valid(a,2*i+1,lo,a[i]) and valid(a,2*i+2,a[i],hi)
        actual = list(map(int,self.compile_and_run(source,''.join(' '.join(map(str,a))+'\n' for a in cases)).split()))
        self.assertEqual(actual,[int(valid(a)) for a in cases])

    def test_2024_unique_topological_order_against_all_permutations(self):
        source = '#include <stdio.h>\n#include <stdlib.h>\n' + r'''
typedef struct { int numVertices; int Edge[4][4]; } MGraph;
''' + self.native_code(2024,41) + r'''
int main(void) {
    for (unsigned mask=0;mask<4096;++mask) {
        MGraph G = {0}; G.numVertices=4; int bit=0;
        for(int i=0;i<4;++i) for(int j=0;j<4;++j)
            if(i!=j) G.Edge[i][j]=(mask>>bit++)&1;
        printf("%d\n",uniquely(G));
    }
    return 0;
}
'''
        actual = list(map(int,self.compile_and_run(source,'').split()))
        edges = [(i,j) for i in range(4) for j in range(4) if i!=j]
        orders = list(itertools.permutations(range(4)))
        expected = []
        for mask in range(4096):
            graph = [edge for k,edge in enumerate(edges) if mask&(1<<k)]
            count = sum(all(order.index(i)<order.index(j) for i,j in graph) for order in orders)
            expected.append(int(count==1))
        self.assertEqual(actual,expected)
