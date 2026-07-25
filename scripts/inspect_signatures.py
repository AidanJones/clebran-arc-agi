"""Check signatures of primitives."""
from clebran.dsl.registry import PRIMITIVES

for name in ['crop', 'dmirror', 'upscale', 'switch', 'compress', 'downscale',
             'hupscale', 'cmirror', 'subgrid', 'cellwise', 'normalize', 'trim',
             'overlap', 'cover', 'recolor', 'shift', 'gravitate', 'move',
             'asobject', 'toobject', 'asindices', 'toindices', 'box', 'frame',
             'inbox', 'corner', 'corners', 'center', 'centers', 'difference',
             'intersection', 'union', 'combine', 'dedupe', 'order', 'size',
             'colorcount', 'mostcolor', 'leastcolor', 'argmax', 'argmin',
             'palette', 'numcolors', 'increment', 'decrement', 'double',
             'halve', 'flip', 'mirror', 'rot2', 'replace', 'fill', 'paint',
             'underfill', 'underpaint', 'move', 'ulcorner', 'urcorner',
             'llcorner', 'lrcorner', 'tojvec', 'toupvec', 'equality',
             'contained', 'occurrences', 'frontiers', 'border', 'fill',
             'hconcat', 'vconcat', 'vmirror', 'hmirror', 'rot90', 'rot180',
             'rot270', 'tophalf', 'bottomhalf', 'lefthalf', 'righthalf']:
    sig = PRIMITIVES.get(name)
    if sig is None:
        continue
    print(f"  {name:14s} arity={sig.arity}, params={[p for p in sig.params]}, returns={sig.returns}")
