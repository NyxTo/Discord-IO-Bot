import re

NUM_RE = re.compile(r'-?(?:(?:[1-9]\d*|0)(?:\.\d*)?|\.\d+)')
IDTF_RE = re.compile(r'[A-Za-z]+')
TOK_RE = re.compile(rf'\s*([+\-*/()]|{NUM_RE.pattern}|{IDTF_RE.pattern}|\S)\s*')
TOLER = {'abs': 1e-9, 'rel': 1e-9}
is_approx = lambda a, b: abs(a - b) < max(TOLER['abs'], TOLER['rel'] * max(abs(a), abs(b)))
INVALID = """Invalid token `{tok}` identified at position `{pos}`.
The only allowed operations are currently: `+`, `-`, `*`, `/`, and parentheses `(`, `)`."""
OUT_DOM = "{calc}: The arguments provided are outside the domain, the function value is not well-defined."

class ParseError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg
class EvalError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg

def recurse(*, num_base, var_base, neg_mod, tree_mod=lambda x: x):
    def deco(accum):
        def wrap(self, *args):
            if self.oper == 'num':
                return num_base(self, *args)
            elif self.oper == 'var':
                return var_base(self, *args)
            elif self.oper == 'neg':
                return neg_mod(wrap(self.value, *args))
            trees = [tree_mod(wrap(val, *args)) for val in self.value]
            stuff = trees[0]
            for op, tree in zip(self.oper, trees[1:]):
                stuff = accum(stuff, op, tree)
            return stuff
        return wrap
    return deco

class AST:
    def __init__(self, oper, value):
        self.oper = oper
        self.value = value
    
    @classmethod
    def from_expr(cls, idcs, fn_exp):
        def parse_expr():
            nonlocal pos
            opers = []
            terms = [parse_term()]
            while pos < len(tokens) and tokens[pos] in ['+', '-']:
                opers.append(tokens[pos])
                pos += 1
                terms.append(parse_term())
            return terms[0] if len(opers) == 0 else cls(opers, terms)
        
        def parse_term():
            nonlocal pos
            opers = []
            facts = [parse_fact()]
            while pos < len(tokens) and tokens[pos] in ['*', '/']:
                opers.append(tokens[pos])
                pos += 1
                facts.append(parse_term())
            return facts[0] if len(opers) == 0 else cls(opers, facts)
        
        def parse_fact():
            nonlocal pos
            neg = False
            while pos < len(tokens) and tokens[pos] == '-':
                neg = not neg
                pos += 1
            if pos >= len(tokens):
                raise ParseError(f"Missing token expected at position {pos}")
            tok = tokens[pos]
            if NUM_RE.fullmatch(tok):
                fact = cls('num', float(tok))
                pos += 1
            elif IDTF_RE.fullmatch(tok):
                if tok not in idcs:
                    raise ParseError(f"The variable `{tok}` used at position `{pos}` is not provided in the list of parameters.")
                fact = cls('var', idcs[tok])
                pos += 1
            elif tok == '(':
                brack = pos
                pos += 1
                expr = parse_expr()
                if tokens[pos] != ')':
                    raise ParseError(f"The open parenthesis `(`at position `{brack}` has no corresponding close parenthesis `)` at position `{pos}`.")
                pos += 1
                fact = expr
            else:
                raise ParseError(INVALID.format(pos=pos))
            return cls('neg', fact) if neg else fact
        
        tokens = TOK_RE.findall(fn_exp)
        pos = 0
        self = parse_expr()
        if len(tokens) > pos:
            raise ParseError(f"Extraneous token `{tokens[pos]}` identified at position `{pos}`, after the end of the expression.")
        return self
    
    
    @recurse(num_base=lambda self, args: self.value,
             var_base=lambda self, args: args[self.value],
             neg_mod=lambda x: -x)
    def eval_at(rslt, op, val):
        if op == '+':
            return rslt + val
        elif op == '-':
            return rslt - val
        elif op == '*':
            return rslt * val
        elif op == '/':
            if val == 0: raise EvalError(OUT_DOM.format(calc="Division by zero"))
            return rslt / val
    
    @recurse(num_base=lambda self, arity: ({(0,) * arity: self.value}, {(0,) * arity: 1}),
             var_base=lambda self, arity: ({tuple(1 if i == self.value else 0 for i in range(arity)): 1}, {(0,) * arity: 1}),
             neg_mod=lambda poly: ({xpn: -coef for xpn, coef in poly[0].items()}, poly[1]))
    def to_poly(poly, op, val):
        top, bottom = poly
        up, down = val
        if op == '+':
            return add_poly(mult_poly(top, down), mult_poly(bottom, up)), mult_poly(bottom, down)
        elif op == '-':
            minus = {xpn: -coef for xpn, coef in mult_poly(bottom, up).items()}
            return add_poly(mult_poly(top, down), minus), mult_poly(bottom, down)
        elif op == '*':
            return mult_poly(top, up), mult_poly(bottom, down)
        elif op == '/':
            return mult_poly(top, down), mult_poly(bottom, up)
    
    def is_ident(self, other, arity):
        top, bottom = self.to_poly(arity)
        up, down = other.to_poly(arity)
        poly1, poly2 = mult_poly(top, down), mult_poly(bottom, up)
        for xpn in poly1 | poly2:
            if not is_approx(poly1.get(xpn, 0), poly2.get(xpn, 0)):
                return False
        return True
    

def add_poly(poly1, poly2):
    total = poly1.copy()
    for xpn, coef in poly2.items():
        total[xpn] = total.get(xpn, 0) + coef
    return total

def mult_poly(poly1, poly2):
    total = {}
    for xpn1, coef1 in poly1.items():
        scaled = {tuple(a + b for a, b in zip(xpn1, xpn2, strict=True)): coef1 * coef2 for xpn2, coef2 in poly2.items()}
        total = add_poly(total, scaled)
    return total
