import os
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ff/miaohui")
from core.config import IMAGE_EXTS, VIDEO_EXTS, EXCLUDED_DIR_NAMES, DEFAULT_ROOTS, load_settings, expand_roots  # noqa

roots = expand_roots(load_settings())
extra = ["~/xsy_mod", "~/vdown_promo", "~/vdown", "~/cubeforge",
         "~/mcbedrock_finder", "~/miyu", "~/LiveWall"]
for r in extra:
    p = Path(os.path.expanduser(r))
    if p.exists():
        roots.append(p)

ni = nv = 0
for r in roots:
    if not r.exists():
        continue
    for dp, dn, fn in os.walk(r):
        dn[:] = [d for d in dn
                 if not d.startswith(".") and d not in EXCLUDED_DIR_NAMES]
        for f in fn:
            e = os.path.splitext(f)[1].lower()
            if e in IMAGE_EXTS:
                ni += 1
            elif e in VIDEO_EXTS:
                nv += 1
print(f"images={ni} videos={nv}")
