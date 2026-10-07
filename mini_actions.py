
"""A small local runner for GitHub Actions workflow files (teaching tool)."""
import os, re, sys, stat, shutil, tempfile, subprocess, itertools, yaml

_SHIM_DIR = None


def _local_env():
    """Make authentic workflow YAML runnable on any machine.

    On a GitHub runner `python` and `pip` always exist and pip may install
    freely. Locally that is not guaranteed, so we (a) provide a `python`
    shim pointing at this interpreter if the name is missing, and (b) allow
    pip to install on externally managed Python installations.
    """
    global _SHIM_DIR
    env = dict(os.environ)
    env.setdefault("PIP_BREAK_SYSTEM_PACKAGES", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    if shutil.which("python") is None and os.name != "nt":
        if _SHIM_DIR is None:
            _SHIM_DIR = tempfile.mkdtemp(prefix="gha-shim-")
            shim = os.path.join(_SHIM_DIR, "python")
            with open(shim, "w") as f:
                f.write('#!/bin/sh\nexec "%s" "$@"\n' % sys.executable)
            os.chmod(shim, os.stat(shim).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        env["PATH"] = _SHIM_DIR + os.pathsep + env.get("PATH", "")
    return env

EXPR = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")


def _resolve(text, ctx):
    if not isinstance(text, str):
        return text
    def sub(m):
        expr = m.group(1).strip()
        for prefix in ("matrix.", "env.", "inputs.", "github."):
            if expr.startswith(prefix):
                return str(ctx.get(prefix[:-1], {}).get(expr[len(prefix):], ""))
        if expr.startswith("secrets."):
            return "***"          # GitHub masks secrets in logs; so do we
        return m.group(0)
    return EXPR.sub(sub, text)


def _expand_matrix(job):
    matrix = (job.get("strategy") or {}).get("matrix")
    if not matrix:
        return [{}]
    keys = list(matrix.keys())
    return [dict(zip(keys, combo)) for combo in itertools.product(*(matrix[k] for k in keys))]


def run_workflow(path, event="push", inputs=None, cwd=None):
    wf = yaml.safe_load(open(path))
    # NOTE: PyYAML reads the bare key `on` as the boolean True (see the pitfalls slide)
    triggers = wf.get("on", wf.get(True, {}))
    if isinstance(triggers, str):
        triggers = {triggers: None}
    if isinstance(triggers, list):
        triggers = {t: None for t in triggers}

    if event not in triggers:
        print(f"[skipped] '{wf.get('name', path)}' does not trigger on '{event}'")
        print(f"          triggers defined: {sorted(triggers)}")
        return {"triggered": False, "ok": True, "jobs": {}}

    wf_env = wf.get("env") or {}
    results, overall_ok = {}, True
    print(f"Workflow: {wf.get('name', path)}   (event: {event})")
    print("=" * 66)

    for job_id, job in (wf.get("jobs") or {}).items():
        needs = job.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        if any(not results.get(n, {}).get("ok", False) for n in needs):
            print(f"\nJob: {job_id}   [skipped - a job it needs did not succeed]")
            results[job_id] = {"ok": False, "skipped": True}
            overall_ok = False
            continue

        job_ok = True
        for combo in _expand_matrix(job):
            label = job_id + (f"  {combo}" if combo else "")
            print(f"\nJob: {label}   runs-on: {job.get('runs-on', 'ubuntu-latest')}")
            print("-" * 66)
            ctx = {"matrix": combo, "env": {**wf_env, **(job.get("env") or {})},
                   "inputs": inputs or {}, "github": {"event_name": event}}
            failed = False
            for step in job.get("steps", []):
                name = _resolve(step.get("name", step.get("uses", step.get("run", "step"))), ctx)
                cond = str(step.get("if", ""))
                if failed and "always()" not in cond:
                    print(f"  [skipped] {name}")
                    continue
                if "uses" in step:
                    print(f"  [action ] {name}   (simulated locally)")
                    continue
                cmd = _resolve(step["run"], ctx)
                env = {**_local_env(),
                       **{k: str(_resolve(v, ctx)) for k, v in ctx["env"].items()},
                       **{k: str(_resolve(v, ctx)) for k, v in (step.get("env") or {}).items()}}
                print(f"  [run    ] {name}")
                for line in cmd.strip().splitlines():
                    if line.strip():
                        print(f"            $ {line.strip()}")
                p = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd, env=env)
                for line in (p.stdout + p.stderr).strip().splitlines()[:20]:
                    print(f"            | {line}")
                if p.returncode != 0:
                    print(f"  [FAILED ] {name}   (exit code {p.returncode})")
                    failed = True
                else:
                    print(f"  [ok     ] {name}")
            job_ok = job_ok and not failed
        results[job_id] = {"ok": job_ok}
        overall_ok = overall_ok and job_ok

    print("\n" + "=" * 66)
    print("RESULT:", "success" if overall_ok else "FAILURE")
    return {"triggered": True, "ok": overall_ok, "jobs": results}
