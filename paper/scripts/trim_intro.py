import sys
p = r'C:\Users\aidan\repos\clebran-arc-agi\paper\01-introduction.md'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

old_section_marker = '## 1.3 The reorientation'
idx = content.find(old_section_marker)
if idx < 0:
    print('Section not found')
    sys.exit(1)

next_section = content.find('## 1.4', idx)
if next_section < 0:
    print('No next section')
    sys.exit(1)

new_section = """## 1.3 The reorientation (preview)

The headline is striking enough to demand a re-reading of the question. The clebran design tried to buy acquisition efficiency by adding *communication* to evolution; the data argue, instead, that the better purchase is to *concentrate* the compute \u2014 one agent that sees every task and reuses its own mined abstractions strictly dominates several agents that see task slices and share. The more interesting question, then, is not \"does communication help?\" but \"does the *way a system learns* change how well it can use what it learned?\" That is Chollet\u2019s re-statement of intelligence as acquisition efficiency, applied at the level of an individual learner. The full argument is delivered in \u00a76.1, where the data have earned it; the contribution list (\u00a71.4) names the two deliverable pieces (the falsification, and a capability audit for what an \u201cacquisition-efficient\u201d learner would need before \u201chow you learned it\u201d can be studied cleanly).

"""

content = content[:idx] + new_section + content[next_section:]

with open(p, 'w', encoding='utf-8') as f:
    f.write(content)

print('Section replaced')
