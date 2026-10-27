import unittest, os, ast, pathfix

class TestCircularDependencies(unittest.TestCase):
    def test_no_circular_dependencies(self):
        bcnc_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../bCNC'))
        
        # Discover all python modules
        mods = {os.path.relpath(os.path.join(r, f), bcnc_dir)[:-3].replace(os.sep, '.'): os.path.join(r, f)
                for r, _, fs in os.walk(bcnc_dir) for f in fs if f.endswith('.py')}
        mods = {m[:-9] if m.endswith('.__init__') else m: p for m, p in mods.items() if m}

        # Build import dependency graph
        graph = {m: set() for m in mods}
        for mod, path in mods.items():
            try:
                with open(path, encoding='utf-8') as f:
                    tree = ast.parse(f.read())
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports = [node.module]
                else:
                    continue

                pkg = mod.rsplit('.', 1)[0] if '.' in mod else ''
                for imp in imports:
                    for cand in {imp, f"{pkg}.{imp}" if pkg else None}:
                        if cand and cand in mods and cand != mod:
                            graph[mod].add(cand)

        # Detect dependency cycles using DFS
        cycles, visited, stack = set(), set(), set()
        def dfs(node, path):
            visited.add(node); stack.add(node); path.append(node)
            for neighbor in graph[node]:
                if neighbor in stack:
                    c = path[path.index(neighbor):] + [neighbor]
                    body = tuple(c[:-1])
                    min_item = min(body)
                    idx = body.index(min_item)
                    cycles.add(body[idx:] + body[:idx])
                elif neighbor not in visited:
                    dfs(neighbor, path)
            path.pop(); stack.remove(node)

        for m in graph:
            if m not in visited:
                dfs(m, [])

        self.assertEqual(len(cycles), 0, f"Circular dependencies found: {list(cycles)}")

if __name__ == '__main__':
    unittest.main()
