"""Route map: does a Departure have more than one road to victory?

Builds the graph of scenes (jumps and choices), finds the scenes that end the Departure
successfully, and reports any scene every route to an ending must pass through.
"""

import qs_ast as A


def edges(scene):
    out = []

    def walk(stmts):
        for st in stmts:
            if isinstance(st, A.Goto):
                out.append(st.scene)
            elif isinstance(st, A.If):
                for _, body in st.branches:
                    walk(body)
            elif isinstance(st, A.Check):
                for body in st.outcomes.values():
                    walk(body)

    walk(scene.body)
    for ch in scene.choices:
        if ch.target:
            out.append(ch.target)
        walk(ch.body)
    return out


def ends_complete(scene):
    def walk(stmts):
        for st in stmts:
            if isinstance(st, A.Command) and st.name == "end" and st.args == ["complete"]:
                return True
            if isinstance(st, A.If) and any(walk(b) for _, b in st.branches):
                return True
            if isinstance(st, A.Check) and any(walk(b) for b in st.outcomes.values()):
                return True
        return False

    return walk(scene.body) or any(walk(ch.body) for ch in scene.choices)


def bottlenecks(dep):
    """Scenes (besides the start and the endings) on every route to an ending.

    Returns (list of scene names, whether any ending is reachable).
    """
    scenes = {s.name: s for s in dep.scenes()}
    if dep.start not in scenes:
        return [], True
    succ = {n: [t for t in edges(s) if t in scenes] for n, s in scenes.items()}
    reach = [dep.start]
    seen = {dep.start}
    for n in reach:
        for t in succ[n]:
            if t not in seen:
                seen.add(t)
                reach.append(t)
    endings = [n for n in reach if ends_complete(scenes[n])]
    if not endings:
        return [], False
    preds = {n: [] for n in reach}
    for n in reach:
        for t in succ[n]:
            preds[t].append(n)
    dom = {n: set(reach) for n in reach}
    dom[dep.start] = {dep.start}
    changed = True
    while changed:
        changed = False
        for n in reach:
            if n == dep.start:
                continue
            ps = [dom[p] for p in preds[n]]
            new = {n} | (set.intersection(*ps) if ps else set())
            if new != dom[n]:
                dom[n] = new
                changed = True
    common = set.intersection(*(dom[e] for e in endings)) - {dep.start} - set(endings)
    return [n for n in reach if n in common], True
