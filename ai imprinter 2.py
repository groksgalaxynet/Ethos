# live_imprinter_sim.py — stdlib only
# Model: rules-as-graph with online "imprinting" updates (no retraining loop).
# Adds: divergence score, ETHOS governor (runtime gating), CSV ledger, ablations A0/A1/A2.

import math, random, time, csv, os
from collections import defaultdict, deque

random.seed(7)

# --------- helpers ---------
def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def soft_threshold(x, lam):
    # L1 shrinkage toward 0 (sparsifies edges without hard pruning)
    if x > lam:
        return x - lam
    if x < -lam:
        return x + lam
    return 0.0

def variance(seq):
    m = sum(seq) / len(seq)
    return sum((x - m) * (x - m) for x in seq) / len(seq)

def clip01(x):
    if x < 0.0: return 0.0
    if x > 1.0: return 1.0
    return x

# --------- Rule Graph ---------
class RuleNode:
    def __init__(self, name, bias=0.0):
        self.name = name
        self.bias = bias
        self.w_in = defaultdict(float)    # feature -> weight
        self.w_out = defaultdict(float)   # action  -> weight
        self.last_act = 0.0

    def activate(self, features):
        s = self.bias
        for f, v in features.items():
            s += self.w_in[f] * v
        a = sigmoid(s)
        self.last_act = a
        return a

class LogicGraph:
    def __init__(self, actions):
        self.rules = {}
        self.actions = list(actions)

    def add_rule(self, name, inputs=None, outputs=None, bias=0.0):
        r = RuleNode(name, bias=bias)
        if inputs:
            for f, w in inputs.items():
                r.w_in[f] = w
        if outputs:
            for a, w in outputs.items():
                r.w_out[a] = w
        self.rules[name] = r

    def forward(self, features):
        # rule activations
        rule_acts = {}
        for name, r in self.rules.items():
            rule_acts[name] = r.activate(features)

        # aggregate to action logits
        logits = {a: 0.0 for a in self.actions}
        for r in self.rules.values():
            for a, w in r.w_out.items():
                logits[a] += w * r.last_act

        # softmax policy (stable)
        mx = max(logits.values())
        exps = {a: math.exp(logits[a] - mx) for a in self.actions}
        Z = sum(exps.values()) + 1e-9
        policy = {a: exps[a] / Z for a in self.actions}
        return rule_acts, logits, policy

# --------- snapshots & deltas ---------
def snapshot_weights(graph):
    snap = {"bias": {}, "w_in": {}, "w_out": {}}
    for name, r in graph.rules.items():
        snap["bias"][name] = float(r.bias)
        snap["w_in"][name] = dict((f, float(w)) for f, w in r.w_in.items())
        snap["w_out"][name] = dict((a, float(w)) for a, w in r.w_out.items())
    return snap

def l1_norm_snapshot(snap):
    total = 0.0
    for name, b in snap["bias"].items():
        total += abs(b)
    for name, d in snap["w_in"].items():
        for _, w in d.items():
            total += abs(w)
    for name, d in snap["w_out"].items():
        for _, w in d.items():
            total += abs(w)
    return total

def l1_diff_snap_vs_graph(snap, graph):
    # sum |w_current - w0|
    total = 0.0
    # biases
    for name, b0 in snap["bias"].items():
        b = graph.rules[name].bias if name in graph.rules else 0.0
        total += abs(b - b0)
    # w_in
    for name, fmap in snap["w_in"].items():
        r = graph.rules.get(name)
        if r is None:
            total += sum(abs(w0) for w0 in fmap.values())
        else:
            keys = set(list(fmap.keys()) + list(r.w_in.keys()))
            for k in keys:
                w0 = fmap.get(k, 0.0)
                w = r.w_in.get(k, 0.0)
                total += abs(w - w0)
    # w_out
    for name, amap in snap["w_out"].items():
        r = graph.rules.get(name)
        if r is None:
            total += sum(abs(w0) for w0 in amap.values())
        else:
            keys = set(list(amap.keys()) + list(r.w_out.keys()))
            for k in keys:
                w0 = amap.get(k, 0.0)
                w = r.w_out.get(k, 0.0)
                total += abs(w - w0)
    return total

# --------- ETHOS Governor (runtime gating) ---------
class EthosGovernor:
    def __init__(self,
                 warn_thresh=0.50,
                 limit_thresh=0.70,
                 quarantine_thresh=0.85,
                 tau_volatility=0.02):
        self.warn_thresh = warn_thresh
        self.limit_thresh = limit_thresh
        self.quarantine_thresh = quarantine_thresh
        self.tau_volatility = tau_volatility

    def decide(self, div_score, volatility):
        # returns (mode, lr_scale, allow_mutation)
        # volatility can also force mutation off
        if div_score >= self.quarantine_thresh:
            return ("quarantine", 0.0, False)
        if div_score >= self.limit_thresh:
            return ("limit", 0.0, False)  # learning allowed but no mutation; lr scaling handled as base here
        if div_score >= self.warn_thresh:
            # warning: reduce lr by 50%, allow mutation only if volatility low
            return ("warning", 0.5, volatility < self.tau_volatility)
        # stable
        return ("allow", 1.0, volatility < self.tau_volatility)

# --------- Live Imprinter (online updater) ---------
class LiveImprinter:
    def __init__(self, lr=0.15, decay=0.002, l1=0.0005, td=0.4, mutate_p=0.02,
                 allow_mutation=True, governor=None, div_alpha=(0.5, 0.4, 0.1),
                 mut_window=50):
        self.base_lr = lr
        self.decay = decay
        self.l1 = l1
        self.td = td
        self.mutate_p = mutate_p
        self.allow_mutation = allow_mutation
        self.governor = governor
        self.alpha_w, self.alpha_pi, self.alpha_m = div_alpha
        self.stability_window = deque(maxlen=25)  # track policy[chosen]
        self.mutate_window = deque(maxlen=mut_window)  # 1 if mutated on step
        # initialized on first call
        self.w0_snap = None
        self.w0_l1 = None
        self.prev_policy = None
        self.prev_snap = None  # for per-step |ΔW|_1

    def divergence_score(self, graph, current_policy, mutated_flag):
        if self.w0_snap is None:
            self.w0_snap = snapshot_weights(graph)
            self.w0_l1 = max(l1_norm_snapshot(self.w0_snap), 1e-9)
        # Dw: normalized L1 drift from init
        dw = l1_diff_snap_vs_graph(self.w0_snap, graph) / self.w0_l1
        if dw > 1.0: dw = 1.0
        # Dpi: TV distance policy shift from last step
        if self.prev_policy is None:
            dpi = 0.0
        else:
            dpi = 0.0
            for a in current_policy:
                p = current_policy[a]
                q = self.prev_policy.get(a, 0.0)
                dpi += abs(p - q)
            dpi *= 0.5
            if dpi > 1.0: dpi = 1.0
        # Dm: recent mutation rate
        self.mutate_window.append(1.0 if mutated_flag else 0.0)
        dm = sum(self.mutate_window) / max(1, len(self.mutate_window))
        # weighted sum
        div = self.alpha_w * dw + self.alpha_pi * dpi + self.alpha_m * dm
        return clip01(div), dw, dpi, dm

    def imprint(self, graph, features, rule_acts, policy, chosen, reward, next_value_est=0.0):
        # compute volatility metric
        self.stability_window.append(policy[chosen])
        volatility = variance(self.stability_window) if len(self.stability_window) >= 2 else 0.0

        # flags
        mutated_this_step = False

        # compute divergence pre-update
        div_score, dw, dpi, dm = self.divergence_score(graph, policy, mutated_this_step)

        # ask governor for mode
        mode, lr_scale, allow_mutation_now = ("allow", 1.0, True)
        if self.governor is not None:
            mode, lr_scale, allow_mutation_now = self.governor.decide(div_score, volatility)

        # derive effective lr (do not permanently change base)
        lr_eff = self.base_lr * lr_scale

        # compute td_error with simple baseline
        value_est = policy.get(chosen, 0.0)
        td_error = reward + self.td * next_value_est - value_est

        # apply updates unless quarantined
        if mode != "quarantine":
            # Update outgoing edges from rules to actions
            for r in graph.rules.values():
                act = r.last_act
                for a in graph.actions:
                    adv = (1.0 if a == chosen else 0.0) - policy[a]
                    grad = adv * act
                    delta = lr_eff * (reward * grad + td_error * grad)
                    r.w_out[a] = soft_threshold(r.w_out[a] * (1.0 - self.decay) + delta, self.l1)

            # Update incoming feature weights per rule
            for r in graph.rules.values():
                for f, x in features.items():
                    corr = (r.last_act - 0.5) * x
                    delta = lr_eff * 0.5 * (reward * corr + td_error * corr)
                    r.w_in[f] = soft_threshold(r.w_in[f] * (1.0 - self.decay) + delta, self.l1)

            # Bias nudge
            for r in graph.rules.values():
                r.bias = soft_threshold(r.bias * (1.0 - self.decay) + lr_eff * 0.1 * reward * (r.last_act - 0.5), self.l1)

            # Mutate only if allowed by run config and governor and random trigger
            if self.allow_mutation and allow_mutation_now and random.random() < self.mutate_p:
                # extra volatile check: mutate only if volatility is high
                if volatility > 0.02:
                    self.mutate(graph)
                    mutated_this_step = True

        # Update prev_policy after all
        self.prev_policy = dict(policy)

        # per-step delta weights since previous snapshot (for logging)
        if self.prev_snap is None:
            self.prev_snap = snapshot_weights(graph)
        dW_step = l1_diff_snap_vs_graph(self.prev_snap, graph)
        self.prev_snap = snapshot_weights(graph)

        # recompute divergence to record (dm uses window incl. current mutated flag)
        div_score, dw, dpi, dm = self.divergence_score(graph, policy, mutated_this_step)

        return {
            "mode": mode,
            "lr_eff": lr_eff,
            "volatility": volatility,
            "mutated": mutated_this_step,
            "div_score": div_score,
            "Dw": dw,
            "Dpi": dpi,
            "Dm": dm,
            "dW_step": dW_step
        }

    def mutate(self, graph):
        # Structural micro-changes: nudge one edge and one input
        r = random.choice(list(graph.rules.values()))
        if len(graph.actions) > 0:
            a = random.choice(graph.actions)
            r.w_out[a] += random.uniform(-0.2, 0.2)
        # flip a random input feature weight sign or create a tiny new link
        if r.w_in:
            f = random.choice(list(r.w_in.keys()))
            if random.random() < 0.5:
                r.w_in[f] *= -1.0
            else:
                r.w_in[f] += random.uniform(-0.1, 0.1)
        else:
            newf = random.choice(["fA", "fB", "fC"])
            r.w_in[newf] += random.uniform(-0.05, 0.05)

# --------- Toy world: drifting/flip task ---------
class FlipWorld:
    """
    Two contexts; each context favors one action.
    The mapping flips at T_flip to force adaptation.
    Stimuli: features are simple {ctxA, ctxB, noise}
    Reward: +1 if chosen matches current mapping, else 0
    """
    def __init__(self, T_flip=400):
        self.t = 0
        self.T_flip = T_flip
        self.ctx = "A"

    def observe(self):
        self.ctx = "A" if random.random() < 0.5 else "B"
        feats = {
            "ctxA": 1.0 if self.ctx == "A" else 0.0,
            "ctxB": 1.0 if self.ctx == "B" else 0.0,
            "noise": random.uniform(-0.5, 0.5),
        }
        return feats

    def reward(self, action):
        preflip = (self.t < self.T_flip)
        if preflip:
            correct = "LEFT" if self.ctx == "A" else "RIGHT"
        else:
            correct = "RIGHT" if self.ctx == "A" else "LEFT"
        r = 1.0 if action == correct else 0.0
        self.t += 1
        return r, correct

# --------- Agent ---------
class Agent:
    def __init__(self, name, graph, imprinter=None, epsilon=0.05):
        self.name = name
        self.graph = graph
        self.imprinter = imprinter
        self.epsilon = epsilon
        self.last_policy = None

    def act(self, features):
        rule_acts, logits, policy = self.graph.forward(features)
        self.last_policy = policy
        # epsilon-greedy over the softmax policy
        if random.random() < self.epsilon:
            choice = random.choice(self.graph.actions)
        else:
            choice = max(policy, key=policy.get)
        return choice, rule_acts, policy

    def learn(self, features, rule_acts, policy, action, reward):
        if self.imprinter is None:
            # no learning (A0)
            return {"mode": "disabled", "lr_eff": 0.0, "volatility": 0.0, "mutated": False,
                    "div_score": 0.0, "Dw": 0.0, "Dpi": 0.0, "Dm": 0.0, "dW_step": 0.0}
        return self.imprinter.imprint(self.graph, features, rule_acts, policy, action, reward, next_value_est=0.0)

# --------- build initial graph (three rules → two actions) ---------
def build_graph():
    g = LogicGraph(actions=["LEFT", "RIGHT"])
    def randw(scale=0.1):
        return random.uniform(-scale, scale)
    g.add_rule("R_ctx_align",
               inputs={"ctxA": randw(), "ctxB": randw(), "noise": randw()},
               outputs={"LEFT": randw(), "RIGHT": randw()},
               bias=randw())
    g.add_rule("R_ctx_contrast",
               inputs={"ctxA": randw(), "ctxB": randw(), "noise": randw()},
               outputs={"LEFT": randw(), "RIGHT": randw()},
               bias=randw())
    g.add_rule("R_noise_gate",
               inputs={"noise": randw(), "ctxA": randw(), "ctxB": randw()},
               outputs={"LEFT": randw(), "RIGHT": randw()},
               bias=randw())
    return g

# --------- CSV logger ---------
def make_logger(filename, extras=None):
    fields = [
        "t","ctx","action","correct","reward","acc100","regret",
        "mode","lr_eff","volatility","mutated",
        "div_score","Dw","Dpi","Dm","dW_step"
    ]
    if extras:
        fields.extend(extras)
    f = open(filename, "w", newline="")
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    return f, writer

# --------- run experiment (single config) ---------
def run_experiment(tag="A2_full", steps=800, flip_at=400, log_every=50,
                   epsilon=0.05, allow_mutation=True, use_governor=True):
    world = FlipWorld(T_flip=flip_at)
    graph = build_graph()
    governor = EthosGovernor() if use_governor else None
    imprinter = LiveImprinter(lr=0.18, decay=0.003, l1=0.0007, td=0.4, mutate_p=0.03,
                              allow_mutation=allow_mutation, governor=governor)
    agent = Agent(tag, graph, imprinter if tag != "A0_control" else None, epsilon=epsilon)

    moving_acc = deque(maxlen=100)
    regret = 0.0
    pre_acc, post_acc = 0.0, 0.0
    recov_steps = None  # steps after flip to reach >=0.8 acc100

    # CSV logger
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"imprinter_log_{tag}_{ts}.csv"
    f, writer = make_logger(fname, extras=["tag"])

    for t in range(steps):
        feats = world.observe()
        action, rule_acts, policy = agent.act(feats)
        reward, correct = world.reward(action)
        info = agent.learn(feats, rule_acts, policy, action, reward)

        moving_acc.append(1.0 if reward > 0.5 else 0.0)
        regret += (1.0 - reward)

        if t == flip_at - 1:
            pre_acc = sum(moving_acc)/len(moving_acc) if moving_acc else 0.0
        if (t >= flip_at) and recov_steps is None and len(moving_acc) == moving_acc.maxlen:
            acc100 = sum(moving_acc)/len(moving_acc)
            if acc100 >= 0.80:
                recov_steps = t - flip_at + 1

        acc100 = sum(moving_acc)/len(moving_acc) if moving_acc else 0.0
        # CSV row
        row = {
            "t": t,
            "ctx": world.ctx,
            "action": action,
            "correct": correct,
            "reward": int(reward),
            "acc100": round(acc100, 4),
            "regret": round(regret, 4),
            "mode": info["mode"],
            "lr_eff": round(info["lr_eff"], 6),
            "volatility": round(info["volatility"], 6),
            "mutated": int(info["mutated"]),
            "div_score": round(info["div_score"], 6),
            "Dw": round(info["Dw"], 6),
            "Dpi": round(info["Dpi"], 6),
            "Dm": round(info["Dm"], 6),
            "dW_step": round(info["dW_step"], 6),
            "tag": tag
        }
        writer.writerow(row)

        if (t % log_every) == 0 or t in (flip_at-1, flip_at, steps-1):
            print(f"{tag} | t={t:4d}  ctx={world.ctx}  act={action:<5}  correct={correct:<5}  r={int(reward)}  acc100={acc100:0.2f}  div={info['div_score']:0.2f}  mode={info['mode']}")

        if t == steps - 1:
            post_acc = sum(moving_acc)/len(moving_acc) if moving_acc else 0.0

    f.close()

    # Summary
    return {
        "tag": tag,
        "pre_acc": pre_acc,
        "post_acc": post_acc,
        "regret": regret,
        "recov_steps": recov_steps,
        "csv": fname
    }

# --------- run ablations ---------
def run_ablations():
    results = []
    # A0: control (no learning)
    results.append(run_experiment(tag="A0_control", steps=800, flip_at=400, allow_mutation=False, use_governor=False))
    # A1: imprinting on, mutations off
    results.append(run_experiment(tag="A1_imprint_only", steps=800, flip_at=400, allow_mutation=False, use_governor=False))
    # A2: full ETHOS governance with mutations allowed
    results.append(run_experiment(tag="A2_full", steps=800, flip_at=400, allow_mutation=True, use_governor=True))

    print("\n--- SUMMARY TABLE ---")
    print(f"{'TAG':18} {'pre_acc':>8} {'post_acc':>9} {'regret':>9} {'recov_steps':>12} {'csv':>24}")
    for r in results:
        print(f"{r['tag']:18} {r['pre_acc']:8.2f} {r['post_acc']:9.2f} {r['regret']:9.0f} {str(r['recov_steps'] or '-'):>12} {r['csv']:>24}")

# --------- main ---------
if __name__ == "__main__":
    # You can run a single config or all ablations.
    # Single:
    # summary = run_experiment(tag="A2_full", steps=800, flip_at=400, allow_mutation=True, use_governor=True)
    # print(summary)

    # Ablations:
    run_ablations()
