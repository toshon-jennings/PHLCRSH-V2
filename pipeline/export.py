"""
export.py — convert raw geodata to GeoParquet for the browser.

Usage:
    python export.py [--out ../app/public/data]

Outputs one GeoParquet file per dataset under --out.
The browser loads these via fetch() on first run, then caches them in OPFS.
"""

import argparse
import pathlib
import geopandas as gpd

OUT_DEFAULT = pathlib.Path(__file__).parent / '../app/public/data'

DATASETS = {
    # key → (input path relative to repo root, layer/sheet if needed)
    'crashes': pathlib.Path('../raw-data/PennDOT Crash Data/collision_crash_2020_2024.geojson'),
    # 'segments': pathlib.Path('../raw-data/Street Centerline Data'),
    # Add more as needed
}


def export_dataset(name: str, src: pathlib.Path, out_dir: pathlib.Path) -> None:
    src = src.resolve()
    out_path = out_dir / f'{name}.parquet'

    print(f'[{name}] reading {src} …')
    gdf = gpd.read_file(src)

    # Reproject to WGS84 (EPSG:4326) — required for MapLibre
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        print(f'[{name}] reprojecting {gdf.crs} → EPSG:4326')
        gdf = gdf.to_crs(epsg=4326)

    print(f'[{name}] writing {len(gdf):,} features → {out_path}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(out_path, index=False, compression='gzip')
    size_mb = out_path.stat().st_size / 1_048_576
    print(f'[{name}] done — {size_mb:.1f} MB')


def main() -> None:
    parser = argparse.ArgumentParser(description='Export raw geo data to GeoParquet')
    parser.add_argument('--out', type=pathlib.Path, default=OUT_DEFAULT)
    parser.add_argument(
        '--datasets',
        nargs='*',
        default=list(DATASETS),
        help='Which datasets to export (default: all)',
    )
    args = parser.parse_args()

    for name in args.datasets:
        if name not in DATASETS:
            print(f'Unknown dataset "{name}". Available: {list(DATASETS)}')
            continue
        export_dataset(name, DATASETS[name], args.out)


if __name__ == '__main__':
    main()
