import glob
import sys
import tarfile
import zipfile

wheels = glob.glob("dist/*.whl")
data = None

if wheels:
    with zipfile.ZipFile(wheels[0]) as z:
        name = next((n for n in z.namelist() if n.endswith("METADATA")), None)
        if not name:
            print("METADATA not found in wheel", file=sys.stderr)
            sys.exit(1)
        data = z.read(name).decode()
else:
    sdists = glob.glob("dist/*.tar.gz")
    if not sdists:
        print("No wheel or sdist found in dist/", file=sys.stderr)
        sys.exit(1)

    with tarfile.open(sdists[0]) as t:
        pkg_info = next((m for m in t.getmembers() if m.name.endswith("PKG-INFO") and m.isfile()), None)
        if not pkg_info:
            print("PKG-INFO not found in sdist", file=sys.stderr)
            sys.exit(1)
        extracted = t.extractfile(pkg_info)
        if extracted is None:
            print("Failed to extract PKG-INFO", file=sys.stderr)
            sys.exit(1)
        data = extracted.read().decode()

for line in data.splitlines():
    if line.startswith("Version:"):
        print(line.split(": ", 1)[1])
        break
else:
    print("Version field not found in metadata", file=sys.stderr)
    sys.exit(1)
