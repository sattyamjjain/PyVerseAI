"""Experiment 02 — dependency-free baselines that set the bar before any ML/API work.

Results on the full labeled set:
  A) ID-extraction (+majority fallback):            0.245  (264 rows covered deterministically)
  B) char-3gram TF-IDF vs catalog:                  0.271 top-1, 0.485 top-5
  C) cascade (ID extraction, else TF-IDF):          0.382
  D) 1-NN over historical requirements (LOO):       0.287; 0.193 excluding near-identical texts

Conclusions: extraction is the strongest single signal; lexical-only retrieval
plateaus quickly (German compounds, near-identical variants); history helps but
mostly via memorization -> motivates hybrid retrieval + LLM rerank.
"""
import sys, re, math
from collections import Counter, defaultdict

sys.path.append(__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from src.load_data import load_products, load_requirements

prods = load_products()
reqs = load_requirements()
catalog_ids = set(prods['product_id'])

text = (reqs['requirement'].fillna('') + ' ' + reqs['requirement_detail'].fillna('')).tolist()
targets = reqs['product_id'].tolist()
most_common = reqs['product_id'].value_counts().idxmax()


def extract_ids(x: str) -> list[str]:
    toks = re.findall(r'\d{7,}', x)
    seen, out = set(), []
    for t in toks:
        if t in catalog_ids and t not in seen:
            seen.add(t)
            out.append(t)
    return out


# ---- Baseline A: ID extraction only (first extracted id, else most-common fallback)
predsA = [ids[0] if (ids := extract_ids(x)) else most_common for x in text]
accA = sum(p == t for p, t in zip(predsA, targets)) / len(targets)
n_extracted = sum(1 for x in text if extract_ids(x))
print(f"A) ID-extraction (+majority fallback): {accA:.3f}  (covers {n_extracted} rows deterministically)")


# ---- char n-gram TF-IDF retrieval
def ngrams(s: str, n: int = 3) -> Counter:
    s = re.sub(r'\s+', ' ', s.lower())
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def build_tfidf(docs: list[str]):
    dfs = Counter()
    tf_list = []
    for d in docs:
        tf = ngrams(d)
        tf_list.append(tf)
        dfs.update(tf.keys())
    N = len(docs)
    idf = {g: math.log(N / (1 + df)) + 1 for g, df in dfs.items()}
    vecs = []
    for tf in tf_list:
        v = {g: (1 + math.log(c)) * idf.get(g, 0.0) for g, c in tf.items()}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        vecs.append({g: w / norm for g, w in v.items()})
    return vecs, idf


prod_docs = (prods['name'].fillna('') + ' ' + prods['description'].fillna('') + ' ' + prods['category'].fillna('')).tolist()
prod_ids = prods['product_id'].tolist()
prod_vecs, idf = build_tfidf(prod_docs)

# inverted index over products
inv = defaultdict(list)
for j, v in enumerate(prod_vecs):
    for g, w in v.items():
        inv[g].append((j, w))


def query_vec(q: str):
    tf = ngrams(q)
    v = {g: (1 + math.log(c)) * idf.get(g, 0.0) for g, c in tf.items()}
    norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
    return {g: w / norm for g, w in v.items()}


def topk(q: str, k: int = 5):
    v = query_vec(q)
    scores = defaultdict(float)
    for g, w in v.items():
        for j, pw in inv.get(g, ()):
            scores[j] += w * pw
    return sorted(scores.items(), key=lambda x: -x[1])[:k]


hit1 = hit5 = 0
predsB = []
for x, t in zip(text, targets):
    tk = topk(x, 5)
    ids = [prod_ids[j] for j, _ in tk]
    predsB.append(ids[0] if ids else most_common)
    hit1 += bool(ids and ids[0] == t)
    hit5 += t in ids
print(f"B) char-3gram TF-IDF vs catalog: top1 {hit1/len(targets):.3f}, top5 {hit5/len(targets):.3f}")

# ---- Baseline C: cascade A -> B
predsC = [a if extract_ids(x) else b for x, a, b in zip(text, predsA, predsB)]
accC = sum(p == t for p, t in zip(predsC, targets)) / len(targets)
print(f"C) cascade (ID extraction, else TF-IDF): {accC:.3f}")

# ---- kNN over historical requirements (leave-one-out, exclude identical text)
req_vecs, _ = build_tfidf(text)
inv_r = defaultdict(list)
for j, v in enumerate(req_vecs):
    for g, w in v.items():
        inv_r[g].append((j, w))

knn_hit = knn_hit_strict = 0
for i, (v, t) in enumerate(zip(req_vecs, targets)):
    scores = defaultdict(float)
    for g, w in v.items():
        for j, pw in inv_r.get(g, ()):
            if j != i:
                scores[j] += w * pw
    if not scores:
        continue
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    knn_hit += targets[ranked[0][0]] == t
    # strict: skip neighbors with near-identical text (sim > 0.95) to simulate unseen requirements
    strict = next((j for j, s in ranked if s <= 0.95), None)
    if strict is not None:
        knn_hit_strict += targets[strict] == t
print(f"D) 1-NN over historical requirements (LOO): {knn_hit/len(targets):.3f}; excluding near-identical (sim>0.95): {knn_hit_strict/len(targets):.3f}")
