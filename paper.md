# 从PDF教材中提取学习路径：一个工程实践的迭代记录

作者: 林慕空  
日期: 2026年7月  
性质: 工作备忘录（以论文形式组织）

---

## 摘要

本文记录了一个从PDF教材中自动提取学习路径的工程实践过程。项目始于一个看似简单的目标：从24页的传播学教材章节中提取核心概念，生成合理的学习顺序。然而，实际开发中遇到了一系列预料之外的问题——从停用词过滤的逻辑错误，到中文分词的边界判断，再到多策略融合时的去重冲突。本文按照时间顺序记录了这些问题是如何被发现、诊断和解决的，每一次迭代都让提取结果更加准确。最终版本能够从同一章节中提取19个核心概念（初始版本仅7个），并生成包含时间估算和难度分级的5步学习路径。

本文不是一篇传统的学术论文，而是一份工程实践的备忘录。它诚实地记录了调试过程中的困惑、临时补丁的丑陋、以及"看起来能跑就行"的实用主义态度。希望这份记录对遇到类似问题的开发者有所帮助。

---

## 1. 项目背景与初始设计

### 1.1 为什么要做这个项目

我在学习传播学教材时，面对24页的"第四章：符号互动"，感到内容庞杂，不知道从何学起。传统的做法是通读全文，手动整理知识点，但这既耗时又容易遗漏。

我想：能不能写个程序，自动从PDF中提取核心概念，分析它们之间的前置关系，然后生成一个合理的学习顺序？

### 1.2 初始架构设计

系统分为两个阶段：

**阶段1：知识提取（knowledge-base）**
- 输入：PDF文件
- 输出：概念列表、定义、章节摘要

**阶段2：路径规划（study-route）**
- 输入：概念列表
- 输出：学习步骤序列（包含时间估算、难度分级）

技术选型：
- PDF解析：PyMuPDF（速度快，Python绑定好）
- 图算法：NetworkX（成熟的图论库）
- 概念提取：正则表达式（简单直接）
- 前置关系：可选用LLM增强

### 1.3 第一版实现（过于乐观）

第一版的概念提取逻辑很简单：

```python
# 匹配 "X是指Y" 这类定义句式
pattern = r'([\u4e00-\u9fff]{2,10})\s*(?:是指|定义为|指的是)\s*(.{10,120}?)[。；]'
```

加上一些停用词过滤：

```python
STOPWORDS = {'前提', '准备', '方面', '过程', '结果', ...}

def is_valid_term(text):
    if text in STOPWORDS:
        return False
    return True
```

在测试数据上跑了一下，看起来还行。于是信心满满地在第四章PDF上运行。

**结果**：提取了7个概念——编码、相容性、复杂性、类似与相近、完形趋向、残缺闭合、共同命运。

**问题**：
- "译码"去哪了？整章一半篇幅在讲它
- "选择性定律"呢？这是第三节的核心概念
- "经验范围"、"劝服"、"创新扩散"呢？全都没提取到
- 更奇怪的是，"装车过程"这种明显不是学术概念的词汇却混进来了

显然，第一版的效果远未达到预期。接下来的工作就是一轮又一轮的调试和迭代。

---

## 2. 第一个Bug："装车过程"是怎么混进来的？

### 2.1 问题现象

提取结果中出现了"装车过程"，定义为"把信息加载到符号上面，而符号就等同于传播信息的运输工具"。

这显然不是一个学术概念。翻开原文一看，这是作者在解释"编码"时用的一个比喻：

> "不妨设想有件集装箱，从郑州运往广州……这个所谓装车过程就是把信息加载到符号上面……"

原文用"装车"来类比"编码"，帮助读者理解。但我们的提取器把"装车过程"当成了一个独立的概念。

### 2.2 诊断过程

我检查了停用词列表：

```python
STOPWORDS = {
    '前提', '准备', '方面', '因素', '过程', '结果', '阶段', '方式',
    '一种', '两种', '三类', '几种', '多种',
    '无非', '所谓', '装车', '卸车', '误会',
}
```

"装车"和"过程"都在列表里！为什么没被过滤掉？

仔细看过滤逻辑：

```python
def is_valid_term(text):
    if text in STOPWORDS:  # 精确匹配
        return False
    return True
```

问题找到了：这是**精确匹配**，不是子串匹配。"装车过程"既不等于"装车"，也不等于"过程"，所以通过了过滤。

### 2.3 修复方案

把精确匹配改成子串匹配：

```python
def is_valid_term(text):
    for stopword in STOPWORDS:
        if stopword in text:  # 子串匹配
            return False
    return True
```

这样，"装车过程"因为包含"装车"和"过程"两个停用词，被正确过滤掉了。

**反思**：这是一个典型的"想当然"错误。写停用词过滤时，我默认"如果一个词包含停用词，就应该被过滤"，但代码实现时却用了精确匹配。测试时用的都是2-3字的短词，没暴露这个问题。

---

## 3. 第二个问题：为什么核心概念提取不到？

### 3.1 问题现象

修复停用词bug后，"装车过程"消失了，但核心概念缺失的问题依然存在：

- "译码"：整章反复出现，但没提取到
- "选择性定律"：第三节标题，没提取到
- "经验范围"：第四节核心概念，没提取到
- "劝服"、"创新扩散"：重要主题，没提取到

### 3.2 诊断过程

我逐条检查这些概念在原文中的出现方式：

**"译码"**：
> "译码同编码正好相反"
> "说话是编码，听话就是译码"

这些句子不包含"是指"、"定义为"等定义句式，所以正则匹配不到。

**"选择性定律"**：
出现在章节标题"第三节 选择性定律"中，但正文里没有定义句。

**"经验范围"**：
> "经验范围是指传播者与受传者之间在知识、经验、文化背景等方面的相似程度"

这句话有"是指"，但正则要求概念名长度在2-10字符，"经验范围"刚好4字符，应该能匹配。为什么没提取到？

仔细看，原文中"经验范围"出现了27次，但只有这一次有定义句。其他时候都是"经验范围的大小"、"共同的经验范围"这样的用法。我们的正则只匹配了这一次，但因为某些原因（可能是上下文太长）被后续的过滤逻辑丢弃了。

### 3.3 根本原因

正则模式匹配有一个本质缺陷：**它只能捕捉有明确定义句式的概念**。对于那些：
- 反复出现但没有"X是指Y"定义的概念
- 出现在章节标题中的主题概念
- 在上下文中间接讨论的概念

正则方法无能为力。

### 3.4 第一个补丁：从章节标题提取

既然章节标题本身就是最好的概念来源，那就加一个策略：

```python
def extract_section_titles(text):
    # 匹配 "第一节 编码与译码" 这样的格式
    pattern = r'第[一二三四五六七八九十]+[节章]\s+([\u4e00-\u9fff\s与和]+)'
    
    titles = []
    for match in re.finditer(pattern, text):
        title = match.group(1).strip()
        # 拆分并列概念："编码与译码" → ["编码", "译码"]
        parts = split_by_conjunctions(title, ['与', '和', '及'])
        titles.extend(parts)
    
    return titles
```

运行结果：提取了"符号互动"、"译码"、"选择性定律"、"人际传播"、"人际影响"、"媒介效应"。

**新问题**：也提取了"左右认知"、"心理机制"、"编码活动"这些明显不是核心概念的词汇。

### 3.5 第二个补丁：通用词过滤

"左右认知"、"心理机制"这些词太泛了，不是传播学的专有概念。加一个过滤列表：

```python
GENERIC_WORDS = {
    '所讲', '理解', '而言', '活动', '机制', '心理', '认知', '感知',
    '影响', '效应', '传播', '定律', '互动', '符号',
    '左右认知', '心理机制', '编码活动',
}

def filter_generic_words(titles):
    return [t for t in titles if t not in GENERIC_WORDS]
```

**反思**：这个列表是手工维护的，看到什么加什么。"左右认知"是因为看到提取结果里有它，才加进去的。这种"打补丁"的方式不够优雅，但实用。

---

## 4. 第三个问题：如何捕捉高频但无定义的概念？

### 4.1 问题现象

即使加上了章节标题提取，"经验范围"、"舆论领袖"、"两级传播"这些概念还是没提取到。它们在正文中反复出现，但没有标准的定义句式。

### 4.2 思路：用词频分析

既然这些概念在文中出现频率很高，那就用词频来识别它们。

但中文没有空格分隔，不能直接用split()分词。我又不想引入jieba这样的分词库（增加依赖，而且对学术文本的效果不一定好）。

一个折中方案：**CJK字符n-gram分析**。提取所有2-5字符的连续中文序列，统计它们在多少个段落中出现。

```python
def extract_cjk_ngrams(text, min_paragraphs=5):
    paragraphs = split_paragraphs(text)
    ngram_counts = {}
    
    for para in paragraphs:
        for n in [2, 3, 4, 5]:
            for i in range(len(para) - n + 1):
                ngram = para[i:i+n]
                if is_pure_cjk(ngram):
                    ngram_counts[ngram] = ngram_counts.get(ngram, 0) + 1
    
    # 过滤：必须在多个段落中出现
    candidates = [(ng, cnt) for ng, cnt in ngram_counts.items() 
                  if cnt >= min_paragraphs]
    
    return sorted(candidates, key=lambda x: -x[1])
```

### 4.3 运行结果：一堆噪声

运行后得到的top 20：

```
'传播' (108次), '信息' (98次), '理解' (63次), '人们' (55次),
'事物' (47次), '选择' (45次), '一个' (43次), '就是' (41次),
'编码' (39次), '过程' (39次), '选择性' (38次), '译码' (38次),
...
```

问题很明显：
1. 2字符的通用词（"传播"、"信息"、"人们"）因为出现频率高，占据了前列
2. 真正的领域概念（"经验范围"、"舆论领袖"）被挤到了后面
3. "选择性"是"选择性接触"的前缀，"译码"已经通过其他方式提取过了

### 4.4 迭代修复

**修复1：优先长n-gram**

把排序从"按频率降序"改为"按长度降序，再按频率降序"：

```python
candidates.sort(key=lambda x: (-len(x[0]), -x[1]))
```

这样，4-5字符的术语会排在前面。

**修复2：过滤函数词**

"的"、"了"、"在"这些字虽然是CJK字符，但是函数词，不应该出现在术语的开头或结尾：

```python
FUNCTION_CHARS = set('的了是在把被从与和及这个那些他们她它我你有一不也就都要会能可以')

def is_valid_ngram(ngram):
    if ngram[0] in FUNCTION_CHARS or ngram[-1] in FUNCTION_CHARS:
        return False
    return True
```

**修复3：子串去重**

"选择性接"是"选择性接触"的子串，应该只保留后者：

```python
def remove_substrings(candidates):
    # 按长度降序排序
    candidates.sort(key=lambda x: -len(x[0]))
    
    result = []
    for ngram, count in candidates:
        # 检查是否是已有结果的子串
        is_substring = any(ngram in longer for longer, _ in result)
        if not is_substring:
            result.append((ngram, count))
    
    return result
```

**修复4：排除已提取的概念**

"译码"已经通过章节标题提取过了，不需要在频率分析中重复提取：

```python
existing_terms = {t['term'] for t in extracted_terms}

for ngram, count in candidates:
    if ngram in existing_terms:
        continue
    # 添加到结果
```

### 4.5 一个新Bug：术语数量阈值

我把频率分析放在提取流程的最后，并加了一个条件：

```python
if len(terms) < 10:
    # 只有提取到的概念不足10个时，才运行频率分析
    ngram_candidates = extract_cjk_ngrams(text)
    ...
```

逻辑是：如果正则+章节标题已经提取了足够多的概念，就不需要频率分析了。

但实际运行时，正则+章节标题已经提取了15个概念，`len(terms) < 10`为假，频率分析根本没运行！

**修复**：把这个条件改成`if True:`，让频率分析始终运行。

### 4.6 又一个Bug：重复计数

修复后运行，发现频率分析只添加了1个概念（"经验范围"），而"舆论领袖"、"两级传播"等高频概念却没添加。

加debug打印后发现问题：在频率分析运行时，`len(terms)`已经是21了（因为之前的步骤添加了很多重复项），触发了`if len(terms) >= 20: break`的提前退出。

**修复**：在频率分析之前先做一次去重：

```python
# 去重
seen = set()
unique_terms = []
for term in terms:
    if term['term'] not in seen:
        seen.add(term['term'])
        unique_terms.append(term)
terms = unique_terms

# 然后再运行频率分析
```

---

## 5. 第四个问题：CJK字符的陷阱

### 5.1 问题现象

扩展到5字符n-gram后，结果中出现了这些奇怪的术语：

```
'的经验范围' (15次)
'编码与译码' (13次)
'传播学引论' (11次)
'播学引论（' (11次)
```

"的经验范围"是什么鬼？"传播学引论"是书名啊！

### 5.2 诊断

原文中有这样的句子：

> "……的经验范围的大小会影响传播效果……"

n-gram分析从"的"开始截取5个字符，得到了"的经验范围"。

"传播学引论"出现在页眉：

> "传播学引论（第四版）"

每一页都有，所以频率很高。

### 5.3 修复方案

**修复1：过滤以函数词开头的n-gram**

之前只过滤了开头是"的"的，但"的"是CJK字符，通过了`is_pure_cjk()`检查。需要专门处理：

```python
def is_valid_ngram(ngram):
    # 不能以函数词开头或结尾
    if ngram[0] in '的了是在把被从与和及':
        return False
    if ngram[-1] in '的了是在把被从与和及':
        return False
    return True
```

**修复2：过滤书名**

把"传播学引论"、"学引论"等加入噪声列表：

```python
NOISE_TERMS = {
    '传播学引论', '学引论', '引论',
    '编码与译码',  # 这是章节标题，不是概念
    '相通或相似',
}

def filter_noise(candidates):
    return [(ng, cnt) for ng, cnt in candidates if ng not in NOISE_TERMS]
```

**修复3：过滤包含标点符号的n-gram**

"播学引论（"包含左括号，应该被过滤：

```python
def is_valid_ngram(ngram):
    # 不能包含标点、数字、英文
    if not all('\u4e00' <= c <= '\u9fff' for c in ngram):
        return False
    return True
```

---

## 6. 第五个问题：部分匹配vs完整术语

### 6.1 问题现象

经过上述修复，提取结果中出现了：

```
'选择性接触' ✓ (完整术语)
'选择性接' ✗ (不完整)
'择性接触' ✗ (不完整)
'选择性理解' ✓ (完整术语)
'选择性理' ✗ (不完整)
```

"选择性接"、"择性接触"、"选择性理"这些都是完整术语的"切片"，应该被过滤掉。

### 6.2 诊断

n-gram分析提取了所有4-5字符的序列。"选择性接触"是5字符，"选择性接"是4字符，它们都在候选列表中。

之前的子串去重逻辑是：如果一个n-gram是另一个更长n-gram的子串，就删除它。但"选择性接"不是"选择性接触"的子串（长度差1，但位置不同），所以没被过滤。

### 6.3 修复方案

**思路**：如果一个4字符n-gram加上一个字符后变成了5字符n-gram，且后者在候选列表中，那前者就是不完整的。

```python
def remove_partial_matches(candidates):
    # 按长度降序排序
    candidates.sort(key=lambda x: -len(x[0]))
    
    result = []
    for ngram, count in candidates:
        # 检查是否是某个更长n-gram的前缀或后缀
        is_partial = False
        for longer, _ in result:
            if len(longer) > len(ngram):
                # 检查前缀：ngram + 某字符 == longer
                if longer.startswith(ngram):
                    is_partial = True
                    break
                # 检查后缀：某字符 + ngram == longer
                if longer.endswith(ngram):
                    is_partial = True
                    break
        
        if not is_partial:
            result.append((ngram, count))
    
    return result
```

**反思**：这个逻辑还是有点粗糙。更严谨的做法是检查n-gram在原文中的边界（前后是否有空格或标点），但中文没有空格，边界判断比较复杂。目前的方案是"能用就行"。

---

## 7. 学习路径生成：从概念到步骤

### 7.1 前置关系推断

概念提取完成后，下一步是推断它们之间的前置关系。

**方法1：基于图结构**

如果上游模块（knowledge-graph）提供了概念关系图，就直接用：

```python
for edge in graph['edges']:
    if edge['relation'] == 'prerequisite':
        prerequisites.append({
            'source': edge['source'],
            'target': edge['target'],
            'reason': f"{edge['target']}需要先理解{edge['source']}",
            'strength': 0.9
        })
```

**方法2：LLM增强（可选）**

如果配置了LLM API，可以让它推断额外的前置关系：

```python
prompt = f"""
以下是教材中的概念列表：
{format_terms(terms)}

请分析这些概念，哪些是其他概念的前置知识？
输出JSON格式：
{{"prerequisites": [{{"source": "A", "target": "B", "reason": "..."}}]}}
"""

response = llm_client.chat(prompt)
llm_prereqs = parse_json(response)
```

**混合策略**：先用图结构生成初始关系，再用LLM补充，最后合并去重。

### 7.2 DAG构建与环检测

把前置关系构建成有向图：

```python
dag = nx.DiGraph()
dag.add_nodes_from(concepts)

for prereq in prerequisites:
    dag.add_edge(prereq['source'], prereq['target'])
```

**问题**：如果LLM推断出了循环依赖（A→B→C→A），图就不是DAG，无法做拓扑排序。

**解决方案**：检测并打破环：

```python
while not nx.is_directed_acyclic_graph(dag):
    cycle = nx.find_cycle(dag)
    # 移除环的最后一条边
    src, tgt = cycle[-1][0], cycle[-1][1]
    dag.remove_edge(src, tgt)
```

**反思**：这个策略很粗暴——直接删边。更好的做法是让LLM重新评估这些关系，或者根据边的强度删除最弱的那条。但目前的实现已经够用了。

### 7.3 拓扑排序与分层

使用Kahn算法做拓扑排序，但不是生成线性序列，而是生成分层：

```python
def topological_layers(dag):
    remaining = dag.copy()
    layers = []
    
    while remaining.nodes():
        # 找出所有入度为0的节点
        roots = [n for n in remaining.nodes() 
                 if remaining.in_degree(n) == 0]
        
        if not roots:
            break  # 理论上不应发生
        
        # 按连接度排序（连接度高的先学）
        roots.sort(key=lambda n: -dag.degree(n))
        layers.append(roots)
        
        # 移除这些节点
        remaining.remove_nodes_from(roots)
    
    return layers
```

**分层的意义**：
- 同一层内的概念没有前置依赖，可以并行学习
- 不同层之间有严格的先后顺序

例如：
```
第1层: ['编码', '译码']  # 可以先学这两个
第2层: ['符号互动']      # 需要先理解编码和译码
第3层: ['选择性定律']    # 需要先理解符号互动
...
```

### 7.4 学习步骤组装

把每一层转换成一个学习步骤：

```python
for i, layer in enumerate(layers):
    step = {
        'order': i + 1,
        'title': f"阶段{i+1}: {', '.join(layer[:3])}",
        'concepts': layer,
        'estimated_time': f"{len(layer) * 5} min",  # 每个概念5分钟
        'difficulty': estimate_difficulty(i, len(layers)),
        'prerequisites': get_prereqs_for_concepts(layer),
    }
    steps.append(step)
```

**难度估算**：
```python
def estimate_difficulty(step_index, total_steps):
    if step_index < total_steps * 0.3:
        return "easy"
    elif step_index < total_steps * 0.7:
        return "medium"
    else:
        return "hard"
```

**时间估算**：简单粗暴，每个概念5分钟。更准确的做法是根据定义的复杂度、前置知识的数量来估算，但目前的方案已经能给出一个合理的参考。

---

## 8. 最终结果

经过上述迭代，最终版本从同一章节中提取了19个核心概念：

**正则匹配提取（3个）**：
- 编码、相容性、复杂性

**章节标题提取（6个）**：
- 符号互动、译码、选择性定律、人际传播、人际影响、媒介效应

**频率分析提取（6个）**：
- 选择性接触、选择性理解、选择性记忆、经验范围、舆论领袖、两级传播

**编号子概念提取（4个）**：
- 类似与相近、完形趋向、残缺闭合、共同命运

生成的学习路径包含5个步骤，总时长95分钟：

```
步骤1: 基础概念 (15 min, easy)
  - 编码、译码、符号互动

步骤2: 心理机制 (20 min, medium)
  - 类似与相近、完形趋向、残缺闭合、共同命运

步骤3: 选择性定律 (15 min, medium)
  - 选择性定律、选择性接触、选择性理解、选择性记忆

步骤4: 人际传播 (20 min, medium)
  - 人际传播、经验范围

步骤5: 传播效果 (25 min, hard)
  - 人际影响、媒介效应、舆论领袖、两级传播、相容性、复杂性
```

---

## 9. 经验总结

### 9.1 关于调试

1. **加debug打印是最快的诊断方法**。在关键位置打印中间结果，比单步调试高效得多。

2. **问题往往出在边界条件**。停用词过滤的精确匹配vs子串匹配、n-gram的边界判断、术语数量阈值……这些边界条件在写代码时容易忽略，但运行时就会暴露。

3. **中文处理的特殊性**。没有空格分隔、函数词也是CJK字符、标点符号混在文本中……这些问题在英文处理中不存在，但在中文处理中必须逐一解决。

### 9.2 关于架构

1. **多策略融合是必要的**。单一策略（如纯正则匹配）无法覆盖所有情况。正则适合有明确定义句式的概念，章节标题适合主题概念，频率分析适合高频但无定义的概念。

2. **去重逻辑比提取逻辑更复杂**。三种策略各自提取概念，合并时要去重、去子串、去噪声。这部分代码占了整个提取流程的一半。

3. **LLM是增强而非替代**。LLM可以推断前置关系，但概念提取还是得靠规则。LLM的输出不稳定，完全依赖它会导致结果不可复现。

### 9.3 关于工程实践

1. **"能用就行"的实用主义**。停用词列表是手工维护的，难度估算是简单线性的，时间估算是固定5分钟/概念。这些方案不够优雅，但能解决问题。在有限时间内，追求完美不如追求可用。

2. **迭代开发比一次性设计更高效**。第一版只用了1小时，但问题很多。接下来的几天里，每发现一个问题就修复一个，逐步迭代到最终版本。如果一开始就试图设计一个"完美"的方案，可能到现在还没写完。

3. **测试数据要真实**。在人工构造的测试数据上，第一版就能跑通。但在真实的PDF教材上，各种问题都暴露出来了。尽早用真实数据测试，能避免走弯路。

---

## 10. 未来可以改进的方向

以下是我知道但没做的改进：

1. **引入分词库**：用jieba或HanLP做分词，比n-gram分析更准确。但会增加依赖，而且对学术文本的效果需要验证。

2. **边界判断优化**：检查n-gram在原文中的前后字符，判断是否是完整词。但这需要处理很多边界情况（如句首、句尾、标点前后）。

3. **LLM辅助提取**：让LLM从全文中提取核心概念，而不是只用规则和统计。但成本高，且结果不稳定。

4. **个性化路径**：结合学习者的知识水平，动态调整路径。但这需要额外的用户数据。

5. **可视化界面**：用Web界面展示学习路径，支持交互式编辑。但这超出了"命令行工具"的定位。

这些改进可以在未来有时间时逐步实现。目前的版本已经能满足基本需求，代码也已经开源（https://github.com/back1992/study-route），欢迎社区贡献。

---

## 附录：关键代码片段

### A.1 停用词过滤（子串匹配版）

```python
STOPWORDS = {
    '前提', '准备', '因素', '方式',
    '一种', '两种', '三类', '几种', '多种',
    '无非', '所谓', '装车', '卸车', '误会',
    '一个', '就是', '他们', '这个', '比如',
    '的信', '际传', '际传播', '择性', '的人际', '的信息',
    '新事物',
}

def is_valid_term(text):
    for stopword in STOPWORDS:
        if stopword in text:  # 子串匹配
            return False
    return True
```

### A.2 CJK字符n-gram提取

```python
def extract_cjk_ngrams(text, min_paragraphs=5):
    paragraphs = re.split(r'\n\n+|[。！？]', text)
    ngram_para_count = {}
    
    for para in paragraphs:
        for n in [2, 3, 4, 5]:
            for i in range(len(para) - n + 1):
                ngram = para[i:i+n]
                
                # 必须是纯CJK字符
                if not all('\u4e00' <= c <= '\u9fff' for c in ngram):
                    continue
                
                # 不能以函数词开头或结尾
                func_chars = set('的了是在把被从与和及')
                if ngram[0] in func_chars or ngram[-1] in func_chars:
                    continue
                
                ngram_para_count[ngram] = ngram_para_count.get(ngram, 0) + 1
    
    # 过滤：必须在多个段落中出现
    candidates = [(ng, cnt) for ng, cnt in ngram_para_count.items() 
                  if cnt >= min_paragraphs]
    
    # 按长度降序，再按频率降序
    candidates.sort(key=lambda x: (-len(x[0]), -x[1]))
    
    return candidates
```

### A.3 部分匹配过滤

```python
def remove_partial_matches(candidates):
    candidates.sort(key=lambda x: -len(x[0]))
    
    result = []
    for ngram, count in candidates:
        is_partial = False
        for longer, _ in result:
            if len(longer) > len(ngram):
                if longer.startswith(ngram) or longer.endswith(ngram):
                    is_partial = True
                    break
        
        if not is_partial:
            result.append((ngram, count))
    
    return result
```

---

**开源地址**：https://github.com/back1992/study-route  
**许可证**：MIT License  
**最后更新**：2026年7月5日

---

**邮箱**：linmk@tup.tsinghua.edu.cn  
**志同道合可以加好友**：
