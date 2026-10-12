"""Conservative AST extraction: summarize unknown regions, continue after them.

No imports/evaluation of model code. A control-region result is an unknown
boundary, not a simulated execution or a selected branch.
"""
import ast
from .analyzer import constant


class GenericAnalyzer:
    def __init__(self, builder, entry, config):
        self.b, self.entry, self.config = builder, entry, config
        self.cls = builder.classes[entry]
        self.method = next((n for n in self.cls.body if isinstance(n, ast.FunctionDef) and n.name == 'forward'), None)
        if self.method is None:
            raise ValueError(f'{entry} 缺少 forward')
        self.scope = builder.scope('model', entry, entry)
        self.registry, self.values, self.env = {}, {}, {}
        self.seq, self.complete, self.continuation = 0, True, None
        self.called = {ast.unparse(n.func) for n in ast.walk(self.method) if isinstance(n, ast.Call)}

    def ref(self, n, constructor=False):
        return self.b.ref(self.entry + ('.__init__' if constructor else '.forward'), n)

    def limit(self, text, n, constructor=False):
        self.complete = False
        self.b.doc['limitations'].append(dict(reason=text, sourceRef=self.ref(n, constructor), scope=self.scope))

    def value(self, n):
        if isinstance(n, ast.Name):
            if n.id in self.values:
                return self.values[n.id]
            if n.id in self.config and type(self.config[n.id]) in (int, bool):
                return self.config[n.id]
            raise ValueError('符号未提供: ' + n.id)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)):
            left, right = self.value(n.left), self.value(n.right)
            ops = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                   ast.Mult: lambda: left * right, ast.FloorDiv: lambda: left // right}
            result = ops[type(n.op)]()
            if type(result) is not int or abs(result) > 1_000_000:
                raise ValueError('尺寸表达式无效或过大')
            return result
        return constant(n, self.config)

    def info(self, path, expression, condition=None, ref_node=None):
        ref_node = ref_node or expression
        ref = self.ref(ref_node, True)
        if isinstance(expression, ast.IfExp):
            test = ast.unparse(expression.test)
            choices = []
            for branch, predicate in [(expression.body, test), (expression.orelse, 'not (' + test + ')')]:
                if isinstance(branch, ast.Constant) and branch.value is None:
                    continue
                choices.append(self.info(path, branch, predicate if condition is None else condition + '; ' + predicate, ref_node))
            self.limit('条件模块注册：保留候选，未判断 ' + test, ref_node, True)
            if len(choices) == 1:
                return choices[0]
            return dict(kind='conditional', instance=None, ref=ref, children=[], out=None, condition=condition)
        fn = ast.unparse(expression.func) if isinstance(expression, ast.Call) else 'external:' + ast.unparse(expression)
        kind = fn.split('.')[-1] if fn.startswith(('nn.', 'torch.nn.')) else 'external'
        shapes, out, children = {}, None, []
        try:
            if kind == 'Linear':
                dims = [self.value(n) for n in expression.args[:2]]
                if len(dims) != 2 or any(type(n) is not int or not 0 < n <= 1_000_000 for n in dims):
                    raise ValueError('Linear 尺寸未确认')
                shapes = {'weight': [dims[1], dims[0]]}
                out = dims[1]
                if next((self.value(k.value) for k in expression.keywords if k.arg == 'bias'), True):
                    shapes['bias'] = [out]
            elif kind == 'Embedding':
                vocab, out = [self.value(n) for n in expression.args[:2]]
                if any(type(n) is not int or not 0 < n <= 1_000_000 for n in [vocab, out]):
                    raise ValueError('Embedding 尺寸未确认')
                shapes = {'weight': [vocab, out]}
            elif kind == 'LayerNorm':
                width = self.value(expression.args[0])
                if type(width) is not int or not 0 < width <= 1_000_000:
                    raise ValueError('LayerNorm 尺寸未确认')
                affine = next((self.value(k.value) for k in expression.keywords if k.arg == 'elementwise_affine'), True)
                bias = next((self.value(k.value) for k in expression.keywords if k.arg == 'bias'), True)
                if affine:
                    shapes['weight'] = [width]
                    if bias:
                        shapes['bias'] = [width]
            elif kind == 'Sequential':
                # Only positional, explicitly declared nn.* modules have known order.
                if expression.keywords or not expression.args or not all(isinstance(n, ast.Call) and ast.unparse(n.func).startswith(('nn.', 'torch.nn.')) for n in expression.args):
                    raise ValueError('Sequential 子模块顺序超出支持范围')
                children = [self.info(f'{path}.{i}', child, condition) for i, child in enumerate(expression.args)]
            elif kind not in ('ReLU', 'SiLU', 'GELU', 'Identity'):
                self.limit('模块内部未解析: ' + fn + '；不推断其参数或子结构', ref_node, True)
        except (ValueError, KeyError, IndexError, ZeroDivisionError) as exc:
            self.limit(f'{path} 的模块尺寸/结构未确认: {exc}', ref_node, True)
            # The source still establishes a Linear/Embedding call, even when dimensions
            # are unknown. Do not erase the module or invent numerical dimensions.
            if kind == 'Linear' and len(expression.args) >= 2:
                try:
                    out = self.value(expression.args[1])
                    if type(out) is not int or not 0 < out <= 1_000_000:
                        out = None
                except (ValueError, KeyError, IndexError, ZeroDivisionError):
                    out = None
        variants = [i for i in self.b.doc['instances'] if i['path'] == path or i['path'].startswith(path + ':variant:')]
        instance_path = path if not variants else path + ':variant:' + str(len(variants))
        module_type = 'torch.nn.' + kind if fn.startswith(('nn.', 'torch.nn.')) else fn
        inst = self.b.instance(instance_path, module_type, shapes, ref)
        self.b.doc['instances'][-1]['config'].update(sourceExpression=ast.unparse(expression), sourceRef=ref, registrationCondition=condition)
        return dict(kind=kind, instance=inst, ref=ref, children=children, out=out, condition=condition)

    def register(self, statements, condition=None):
        for stmt in statements:
            if isinstance(stmt, ast.With):
                context = ', '.join(ast.unparse(item.context_expr) for item in stmt.items)
                self.limit('构造器 with 上下文：提取其中声明，保留进入上下文条件；未执行 ' + context, stmt, True)
                self.register(stmt.body, context if condition is None else condition + '; ' + context)
            elif isinstance(stmt, ast.If):
                predicate = ast.unparse(stmt.test)
                self.limit('构造器动态控制流：保留条件模块声明，参数统计未确认: ' + predicate, stmt, True)
                self.register(stmt.body, predicate if condition is None else condition + '; ' + predicate)
                self.register(stmt.orelse, 'not (' + predicate + ')' if condition is None else condition + '; not (' + predicate + ')')
            elif isinstance(stmt, (ast.For, ast.While, ast.Try)):
                self.limit('构造器动态控制流：循环/异常中的注册及共享关系未确认', stmt, True)
                # Do not enumerate hypothetical loop instances or assume execution.
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = ast.unparse(stmt.targets[0])
                if isinstance(stmt.targets[0], ast.Name):
                    try:
                        self.values[target] = self.value(stmt.value)
                    except (ValueError, KeyError, ZeroDivisionError):
                        pass
                    continue
                if not target.startswith('self.'):
                    continue
                if target.count('.') > 1:
                    self.limit('参数属性赋值/复杂共享未确认：' + target, stmt, True)
                    continue
                value = ast.unparse(stmt.value)
                if value in self.registry and len(self.registry[value]) == 1:
                    original = self.registry[value][0]
                    inst = self.b.instance(target[5:], 'alias:' + value, {}, self.ref(stmt, True))
                    new = self.b.doc['instances'][-1]
                    parent = next(i for i in self.b.doc['instances'] if i['id'] == original['instance'])
                    new['parameterIds'] = list(parent['parameterIds'])
                    for parameter in self.b.doc['parameters']:
                        if parameter['id'] in new['parameterIds']:
                            parameter['instances'].append(inst)
                            parameter['shared'] = True
                    self.registry.setdefault(target, []).append({**original, 'instance': inst, 'condition': condition})
                elif isinstance(stmt.value, (ast.Call, ast.IfExp)) or isinstance(stmt.value, ast.Name) and target in self.called:
                    call = stmt.value.body if isinstance(stmt.value, ast.IfExp) else stmt.value
                    fn = ast.unparse(call.func) if isinstance(call, ast.Call) else None
                    if fn in ('nn.Parameter', 'torch.nn.Parameter'):
                        self.limit('独立 Parameter 注册未解析，不将其伪装为模块', stmt, True)
                    elif fn and (fn.startswith(('nn.', 'torch.nn.')) or target in self.called) or isinstance(call, ast.Name) and target in self.called:
                        self.registry.setdefault(target, []).append(self.info(target[5:], stmt.value, condition, stmt))
                    elif fn:
                        self.limit('属性调用结果的类型未确认，不当作模块注册: ' + target, stmt, True)

    def shape(self, node):
        return next(t['shape'] for t in self.b.doc['tensors'] if t['id'] == self.b.outputs[node])

    def node(self, label, role, inputs, shape, source, instance=None, child=None, opaque=False, scope=None, dtype='unknown', calculation=None, condition=None):
        self.seq += 1
        node = self.b.node(scope or self.scope, f'call:{self.seq}', label[:110], role, list(dict.fromkeys(inputs)), shape, self.ref(source), instance, child, dtype, opaque, calculation)
        predicate = condition or self.continuation
        if predicate:
            for edge in self.b.doc['edges']:
                if edge['id'].startswith(node + ':edge'):
                    edge['condition'] = predicate
        return node

    def module(self, info, args, source, label, scope=None):
        kind, out, child = info['kind'], [None], None
        role = kind.lower() if kind in ('Linear', 'Embedding', 'LayerNorm', 'ReLU', 'SiLU', 'GELU', 'Identity', 'Sequential') else 'opaque'
        if role in ('linear', 'embedding') and info['out'] is not None:
            prior = self.shape(args[0]) if args else [None]
            if prior != [None]:
                out = prior[:-1] + [info['out']] if role == 'linear' else prior + [info['out']]
        elif role in ('layernorm', 'relu', 'silu', 'gelu', 'identity') and args:
            out = self.shape(args[0])
        if kind == 'Sequential' and len(args) == 1 and info['children']:
            child = f'{scope or self.scope}/sequence:{self.seq + 1}'
        node = self.node(label, role, args, out, source, info['instance'], child, role == 'opaque', scope, condition=info['condition'])
        if role in ('linear', 'embedding') and info['out'] is not None:
            explanation = next(e for e in self.b.doc['explanations'] if e['id'] == 'ex:' + node)
            explanation['calculation'] = f'源码声明输出末维为 {info["out"]}；输入 rank/前缀未提供时，完整形状保留未知，不假设为二维或三维。'
        if child:
            self.b.scope(child, label, self.entry, scope or self.scope, node)
            self.b.doc['scopes'][-1]['sourceRef'] = info['ref']
            inp = self.node('输入', 'input', [], self.shape(args[0]), source, scope=child)
            current = inp
            for index, item in enumerate(info['children']):
                current = self.module(item, [current], source, f'{index}: {item["kind"]}', child)
                # Internal calculation belongs to the actual constructor expression,
                # not to a fabricated forward definition of a torch builtin.
                entry_node = next(n for n in self.b.doc['nodes'] if n['id'] == current)
                entry_node['sourceRef'] = item['ref']
                explanation = next(e for e in self.b.doc['explanations'] if e['id'] == entry_node['explanation'])
                for ident in explanation['evidence']:
                    next(e for e in self.b.doc['evidence'] if e['id'] == ident)['sourceRefs'] = [item['ref']]
            output = self.node('输出', 'output', [current], self.shape(current), source, scope=child)
            # Parent output shape follows the last explicitly declared child.
            next(t for t in self.b.doc['tensors'] if t['id'] == self.b.outputs[node])['shape'] = self.shape(current)
            self.b.bind(child, node, inp, output)
        return node

    def expr(self, n):
        if isinstance(n, ast.Name) and n.id in self.env:
            return self.env[n.id]
        if isinstance(n, (ast.Tuple, ast.List)):
            return [self.expr(item) for item in n.elts]
        args, role, shape, dtype = [], 'opaque', [None], 'unknown'
        if isinstance(n, ast.Constant):
            return self.node(repr(n.value), 'constant', [], [], n, dtype=type(n.value).__name__)
        if isinstance(n, ast.BinOp):
            args = [self.expr(n.left), self.expr(n.right)]
            role = {ast.Add: 'add', ast.Mult: 'mul', ast.Sub: 'sub', ast.Div: 'div'}.get(type(n.op), 'opaque')
            if self.shape(args[0]) == self.shape(args[1]):
                shape = self.shape(args[0])
        elif isinstance(n, ast.Call):
            fn = ast.unparse(n.func)
            # Preserve the receiver of h.detach(), self.scorer(m).squeeze(), etc.
            if isinstance(n.func, ast.Attribute) and not isinstance(n.func.value, ast.Name):
                args.append(self.expr(n.func.value))
            elif isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id in self.env:
                args.append(self.expr(n.func.value))
            for value in [*n.args, *(k.value for k in n.keywords if k.arg not in ('dim', 'axis', 'inplace'))]:
                if isinstance(value, ast.Constant) or isinstance(value, ast.UnaryOp) and isinstance(value.operand, ast.Constant):
                    continue
                result = self.expr(value)
                args.extend(result if isinstance(result, list) else [result])
            if fn in self.registry:
                choices = self.registry[fn]
                if len(choices) == 1:
                    return self.module(choices[0], args, n, fn)
                self.limit('模块存在多个注册候选，不选择一项: ' + fn, n)
            elif fn in ('torch.relu', 'F.relu', 'torch.silu', 'F.silu', 'F.gelu', 'torch.softmax', 'F.softmax', 'torch.log'):
                role = fn.split('.')[-1]
                shape = self.shape(args[0]) if args else [None]
            elif fn in ('torch.cat', 'torch.concat', 'torch.stack', 'torch.gather'):
                role = fn.split('.')[-1]
            elif isinstance(n.func, ast.Attribute) and args:
                name = n.func.attr
                if name in ('detach', 'contiguous', 'clone'):
                    role, shape = name, self.shape(args[0])
                elif name in ('float', 'bool'):
                    role, shape, dtype = 'cast', self.shape(args[0]), 'float32' if name == 'float' else 'bool'
                elif name in ('reshape', 'view', 'transpose', 'squeeze', 'unsqueeze', 'expand', 'clamp', 'clamp_min', 'sum', 'masked_fill', 'to', 'size'):
                    role = name
        elif isinstance(n, (ast.Attribute, ast.Subscript)):
            if not isinstance(n.value, ast.Name) or n.value.id in self.env:
                args.append(self.expr(n.value))
            if isinstance(n, ast.Subscript):
                for name in sorted({x.id for x in ast.walk(n.slice) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id in self.env}):
                    if self.env[name] not in args:
                        args.append(self.env[name])
            role = 'field' if isinstance(n, ast.Attribute) else 'index'
        elif isinstance(n, ast.UnaryOp):
            args = [self.expr(n.operand)]
            role = 'unary'
            shape = self.shape(args[0])
        if role == 'opaque':
            self.limit('不支持表达式，保留真实输入边界: ' + ast.unparse(n), n)
        # Recursively parsed operands/arguments already contain their dependencies.
        # Do not create shortcuts from grandchildren to this operation.
        if role == 'opaque' and not args:
            for name in sorted({x.id for x in ast.walk(n) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id in self.env}):
                args.append(self.env[name])
        return self.node(ast.unparse(n), role, args, shape, n, opaque=role == 'opaque', dtype=dtype)

    def control(self, stmt, future):
        self.limit('动态控制流/循环：内部 opaque，保留变量出口并继续读取后续源码；未选择路径或枚举重复层', stmt)
        reads = sorted({n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id in self.env})
        inputs = [self.env[name] for name in reads]
        # An unrecognized statement may mutate an input even without rebinding it.
        writes = sorted({n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)})
        live = {n.id for later in future for n in ast.walk(later) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        condition = ast.unparse(stmt.test) if isinstance(stmt, (ast.If, ast.While)) else ast.unparse(stmt).split('\n')[0]
        boundary = self.node(condition + '（内部未展开）', 'opaque', inputs, [None], stmt, opaque=True)
        for name in writes:
            if name not in live:
                continue
            sources = [boundary]
            definitely_written = set()
            def definite(statements):
                result = set()
                for statement in statements:
                    if isinstance(statement, ast.Assign):
                        result.update(t.id for t in statement.targets if isinstance(t, ast.Name))
                    elif isinstance(statement, ast.If) and statement.orelse:
                        result.update(definite(statement.body) & definite(statement.orelse))
                return result
            if isinstance(stmt, ast.If) and stmt.orelse:
                definitely_written = definite(stmt.body) & definite(stmt.orelse)
            if name in self.env and name not in definitely_written:
                sources.append(self.env[name])
            self.env[name] = self.node('条件结果 ' + name, 'conditional_result', sources, [None], stmt, opaque=True, calculation='分支/循环结果及可能保留的旧值；未判断条件，未确认尺寸。', condition='变量结果来自控制区域: ' + condition)
        # Keep potential early returns, then qualify all subsequent dependencies.
        returns = [n for n in ast.walk(stmt) if isinstance(n, ast.Return)]
        for n in returns:
            self.node('条件返回 ' + ast.unparse(n.value), 'output', [boundary], [None], n, opaque=True, condition='可能在控制区域内提前返回: ' + condition)
        if returns:
            self.continuation = '仅在控制区域未提前返回的路径: ' + condition
        if not writes and not returns:
            for name in reads:
                if name in live:
                    self.env[name] = self.node('未知语句后的 ' + name, 'conditional_result', [boundary, self.env[name]], [None], stmt, opaque=True)

    def run(self):
        init = next((n for n in self.cls.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'), None)
        if init:
            self.register(init.body)
        for arg in [*[*self.method.args.posonlyargs, *self.method.args.args][1:], *self.method.args.kwonlyargs]:
            self.env[arg.arg] = self.b.node(self.scope, 'input:' + arg.arg, arg.arg, 'input', [], [None], self.ref(self.method), dtype='unknown')
        statements = self.method.body
        for index, stmt in enumerate(statements):
            if isinstance(stmt, ast.Assign) and all(isinstance(t, ast.Name) for t in stmt.targets):
                value = self.expr(stmt.value)
                if isinstance(value, list):
                    self.control(stmt, statements[index + 1:])
                else:
                    for target in stmt.targets:
                        self.env[target.id] = value
            elif isinstance(stmt, ast.Return):
                values = stmt.value.elts if isinstance(stmt.value, (ast.Tuple, ast.List)) else [stmt.value]
                for i, expression in enumerate(values):
                    node = self.expr(expression)
                    self.node('输出 ' + ast.unparse(expression), 'output', [node], self.shape(node), stmt)
                break
            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                continue # A docstring is source data, not an executable dependency.
            else:
                self.control(stmt, statements[index + 1:])
        self.b.doc['limitations'].append(dict(reason='通用 AST 局部提取：条件/循环内部不展开；继续保留后续计算和多输出。仅直接声明的 nn.Sequential 可进入。外部注入模块、未知尺寸、共享及训练条件不作运行验证或参数估算。', sourceRef=self.b.symbols[self.entry], scope=self.scope))
        doc = self.b.finish(self.complete)
        for evidence in doc['evidence']:
            if evidence['kind'] == 'static':
                evidence['assumptions'] = ['仅静态 AST 和明确配置/模块声明；未运行模型', '没有输入契约时不假设完整 rank/shape/dtype；条件分支未选择']
        return doc


def analyze_generic(builder, entry, config):
    return GenericAnalyzer(builder, entry, config).run()
