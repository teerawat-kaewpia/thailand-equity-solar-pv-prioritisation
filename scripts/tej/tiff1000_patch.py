"""One-off patch (2026-10-15): every figure script also writes a 1000 dpi TIFF through _figures.save_tiff.

After each 600 dpi PNG save of a registered figure, a save_tiff() call with the same layout arguments is
added. Direct scripts are edited here. The generated scripts get the same rule from
make_supp_fig_scripts_tej.py (function add_tiff).
"""
import re
from pathlib import Path

S = Path(__file__).resolve().parent
PNG = re.compile(r'^(\s*)(\w+)\.savefig\(str\(figout\("([a-z-]+)"\)\), dpi=600, (.*?)\)\s*(#.*)?$')


def add_tiff(s):
    out, n = [], 0
    for line in s.splitlines(keepends=True):
        out.append(line)
        m = PNG.match(line.rstrip("\n"))
        if m:
            ind, var, key, kw = m.group(1), m.group(2), m.group(3), m.group(4)
            out.append(f'{ind}save_tiff({var}, "{key}", {kw})   # 1000 dpi TIFF\n')
            n += 1
    s = "".join(out)
    s = s.replace("from _figures import figout ", "from _figures import figout, save_tiff ", 1)
    return s, n


if __name__ == "__main__":
    for rel in ("figures/fig01_framework_tej.py", "figures/fig02_study_area_tej.py", "figures/fig03_input_layers_tej.py",
                "figures/fig06_07_pai_zone_maps_tej.py", "figures/fig10_deployment_scatter_tej.py",
                "figures/fig13_14_radar_policy_tej.py"):
        p = S / rel
        s = p.read_text(encoding="utf-8")
        if "save_tiff(" in s:
            print("already", rel)
            continue
        s, n = add_tiff(s)
        assert n >= 1 and "figout, save_tiff" in s, (rel, n)
        p.write_text(s, encoding="utf-8")
        print(f"patched {rel}: {n} TIFF call(s)")
