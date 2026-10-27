"""Minimal KiCad S-expression parser / writer that keeps quoted vs bare atoms."""
import re, copy


class Q(str):
    """A quoted string atom."""


_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def parse(text):
    stack = [[]]
    for m in _TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        elif t.startswith('"'):
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


_INLINE = {'at', 'xy', 'size', 'start', 'end', 'mid', 'length', 'stroke', 'fill', 'color', 'width', 'type',
           'font', 'justify', 'hide', 'offset', 'unit', 'uuid', 'diameter', 'lib_id', 'reference', 'page',
           'exclude_from_sim', 'in_bom', 'on_board', 'dnp', 'fields_autoplaced', 'shape', 'thickness', 'bold',
           'italic', 'pin_numbers', 'pin_names', 'radius', 'center', 'mirror', 'convert', 'name', 'number',
           'embedded_fonts', 'paper', 'version', 'generator', 'generator_version', 'title', 'date', 'rev',
           'company', 'comment', 'power', 'effects', 'pts', 'extends', 'body_style'}


def dump(node, ind=0):
    if not isinstance(node, list):
        return _atom(node)
    head = node[0] if node else ''
    simple = all(not isinstance(c, list) for c in node)
    if simple or (head in _INLINE and sum(len(dump(c)) for c in node) < 160):
        return '(' + ' '.join(dump(c) for c in node) + ')'
    out = '(' + _atom(node[0])
    i = 1
    # keep leading atoms on the head line
    while i < len(node) and not isinstance(node[i], list):
        out += ' ' + _atom(node[i])
        i += 1
    for c in node[i:]:
        out += '\n' + '\t' * (ind + 1) + dump(c, ind + 1)
    out += '\n' + '\t' * ind + ')'
    return out


def find(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def first(node, name):
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def prop(node, name):
    for c in find(node, 'property'):
        if c[1] == name:
            return c
    return None


def deep(node):
    return copy.deepcopy(node)
