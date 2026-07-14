# Geospatial environment setup

Read this file only when Cartopy, Rasterio, Fiona, GeoPandas, GDAL, or related
geospatial imports fail or emit an environment warning. Do not load it for every map.

## Windows and conda

On Windows conda environments, geospatial packages can emit warnings such as
`GDAL_DATA is not defined` even when plotting succeeds. When the active environment
contains GDAL's data directory, set it before importing geospatial packages:

```python
import os
from pathlib import Path
import sys

gdal_data = Path(sys.prefix) / "Library" / "share" / "gdal"
if "GDAL_DATA" not in os.environ and gdal_data.exists():
    os.environ["GDAL_DATA"] = str(gdal_data)
```

Do not install or switch plotting stacks solely to remove a benign warning. First
check whether the requested projection, vector/raster read, render, and saved
artifacts are correct. Treat warnings as blocking only when they indicate missing
data files, ignored CRS/transform arguments, invalid coordinates, failed imports, or
incorrect output.

## Minimal diagnosis

Use the task's required environment and a temporary probe outside the delivery
directory. Check only the failing layer:

1. import the named package and report its version;
2. inspect `sys.executable`, `sys.prefix`, and relevant data directories;
3. load the smallest real input or a minimal geometry/raster;
4. render once with the required CRS/transform;
5. stop after a successful result or one targeted warning-removal attempt.

Do not copy environment probes, logs, caches, or helper scripts into the user's
delivery directory.
