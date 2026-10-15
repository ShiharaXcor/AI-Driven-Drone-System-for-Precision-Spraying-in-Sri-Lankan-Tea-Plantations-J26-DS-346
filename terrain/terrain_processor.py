# terrain_processor.py
# Component 3 — Terrain Processing Module
# Processes Kenilworth GeoTIFF orthophoto + NASA SRTM real elevation data
# Produces heightmap for Gazebo and accurate slope grid for energy model
#
# Run from Ubuntu terminal:
#   cd ~/component3
#   source venv/bin/activate
#   python3 terrain/terrain_processor.py

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os
import json
import xml.etree.ElementTree as ET
import rasterio
from rasterio.windows import Window, from_bounds

def get_tiff_info(tiff_path):
    """Print information about the TIFF file without loading it fully."""
    print(f"Reading TIFF info: {tiff_path}")
    with rasterio.open(tiff_path) as ds:
        print(f"  Full size:     {ds.width} x {ds.height} pixels")
        print(f"  Bands:         {ds.count}")
        print(f"  CRS:           {ds.crs}")
        print(f"  Bounds:        {ds.bounds}")
        transform      = ds.transform
        pixel_size_deg = abs(transform.a)
        pixel_size_m   = pixel_size_deg * 111320
        print(f"  Pixel size:    {pixel_size_deg:.8f} deg = {pixel_size_m:.4f} m")
        return ds.width, ds.height, pixel_size_m, ds.bounds


def parse_kml_boundary(kml_path):
    """Extract estate boundary coordinates from KML file."""
    tree        = ET.parse(kml_path)
    root        = tree.getroot()
    coords_text = None
    for elem in root.iter():
        if 'coordinates' in elem.tag:
            coords_text = elem.text.strip()
            break
    points = []
    for point in coords_text.split():
        parts = point.split(',')
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return min(lons), max(lons), min(lats), max(lats)


def generate_heightmap(elevation, output_path, target_size=513):
    """Generate Gazebo-compatible greyscale heightmap PNG."""
    print(f"\nGenerating heightmap ({target_size} x {target_size})...")
    valid    = elevation[~np.isnan(elevation)]
    elev_min = valid.min()
    elev_max = valid.max()
    elev_filled = np.where(np.isnan(elevation), elev_min, elevation)
    if elev_max > elev_min:
        normalised = ((elev_filled - elev_min) / (elev_max - elev_min) * 255)
    else:
        normalised = np.zeros_like(elev_filled)
    normalised  = np.clip(normalised, 0, 255).astype(np.uint8)
    img         = Image.fromarray(normalised, mode='L')
    img_resized = img.resize((target_size, target_size), Image.LANCZOS)
    img_resized.save(output_path)
    metadata = {
        "heightmap_size_pixels": target_size,
        "pixel_value_min":       float(elev_min),
        "pixel_value_max":       float(elev_max),
        "gazebo_world_size_m":   2546,
        "gazebo_height_scale_m": 526,
        "source":                "Kenilworth orthophoto (visual) + SRTM elevation (physics)",
        "heightmap_file":        output_path
    }
    meta_path = output_path.replace('.png', '_metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"  Heightmap saved:  {output_path}")
    print(f"  Metadata saved:   {meta_path}")
    return elev_min, elev_max


def process_orthophoto(tiff_path, heightmap_path, viz_path):
    """
    Process Kenilworth orthophoto for Gazebo visual appearance.
    Uses KML boundary window. Visual only — not for slope calculation.
    """
    print(f"\n{'='*60}")
    print("ORTHOPHOTO PROCESSING — Kenilworth GeoTIFF")
    print("Used for: Gazebo 3D terrain visual appearance")
    print(f"{'='*60}")

    col_off = 0
    row_off = 3899
    win_w   = 84878
    win_h   = 46490

    print(f"\nLoading full estate (downsampled 50x)...")
    with rasterio.open(tiff_path) as ds:
        window = Window(col_off, row_off,
                        min(win_w, ds.width  - col_off),
                        min(win_h, ds.height - row_off))
        out_w  = win_w // 50
        out_h  = win_h // 50
        photo  = ds.read(
            1, window=window,
            out_shape=(out_h, out_w),
            resampling=rasterio.enums.Resampling.average
        ).astype(np.float32)

    photo[photo <= 0] = np.nan
    valid = photo[~np.isnan(photo)]
    print(f"  Loaded size:  {photo.shape}")
    print(f"  Valid pixels: {len(valid):,} ({len(valid)/photo.size*100:.1f}%)")
    print(f"  Coverage:     ~2546m x 1395m (full estate)")

    generate_heightmap(photo, heightmap_path)

    # Visualise orthophoto
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    fig.suptitle(
        'Ouvahkelle Estate — Kenilworth International Orthophoto\n'
        'Used for Gazebo 3D terrain visual appearance',
        fontsize=13, fontweight='bold'
    )
    im = ax.imshow(photo, cmap='terrain',
                    vmin=valid.min(), vmax=valid.max())
    ax.set_title(f'Full estate: ~2546m x 1395m\n'
                  f'Source: Kenilworth International (data sharing agreement)',
                  fontsize=11)
    ax.set_xlabel('East →')
    ax.set_ylabel('North ↑')
    plt.colorbar(im, ax=ax, label='Pixel value')
    plt.tight_layout()
    plt.savefig(viz_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Orthophoto visualisation: {viz_path}")

    return photo


def process_srtm(srtm_path, kml_path, output_dir):
    """
    Process NASA SRTM elevation data for accurate slope calculation.
    This is the data used by the energy model — real metres above sea level.
    """
    print(f"\n{'='*60}")
    print("SRTM ELEVATION PROCESSING — NASA SRTM 30m")
    print("Used for: Energy model slope input (real elevation in metres)")
    print(f"{'='*60}")

    min_lon, max_lon, min_lat, max_lat = parse_kml_boundary(kml_path)
    print(f"\nEstate boundary from KML:")
    print(f"  Longitude: {min_lon:.4f} to {max_lon:.4f}")
    print(f"  Latitude:  {min_lat:.4f} to {max_lat:.4f}")

    with rasterio.open(srtm_path) as ds:
        pixel_size_deg = abs(ds.transform.a)
        pixel_size_m   = pixel_size_deg * 111320
        window         = from_bounds(min_lon, min_lat,
                                     max_lon, max_lat,
                                     ds.transform)
        elevation      = ds.read(1, window=window).astype(np.float32)

    elevation[elevation < -100] = np.nan

    valid = elevation[~np.isnan(elevation)]
    print(f"\nReal elevation data:")
    print(f"  Grid size:       {elevation.shape}")
    print(f"  Pixel size:      {pixel_size_m:.1f} m (SRTM 30m resolution)")
    print(f"  Min elevation:   {valid.min():.1f} m above sea level")
    print(f"  Max elevation:   {valid.max():.1f} m above sea level")
    print(f"  Elevation range: {valid.max()-valid.min():.1f} m")
    print(f"  Mean elevation:  {valid.mean():.1f} m")

    # Compute accurate slope from real elevation
    dz_dy, dz_dx = np.gradient(elevation, pixel_size_m)
    slope_rad     = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg     = np.degrees(slope_rad)
    slope_deg[np.isnan(elevation)] = np.nan

    valid_slope = slope_deg[~np.isnan(slope_deg)]
    print(f"\nReal slope analysis (from SRTM elevation):")
    print(f"  Min slope:          {valid_slope.min():.1f} degrees")
    print(f"  Max slope:          {valid_slope.max():.1f} degrees")
    print(f"  Average slope:      {valid_slope.mean():.1f} degrees")
    print(f"  Flat  (0-5 deg):    {(valid_slope<5).mean()*100:.1f}%")
    print(f"  Moderate (5-20):    {((valid_slope>=5)&(valid_slope<20)).mean()*100:.1f}%")
    print(f"  Steep (>20 deg):    {(valid_slope>=20).mean()*100:.1f}%")

    # Save
    slope_path = os.path.join(output_dir, "slope_grid_srtm.npy")
    elev_path  = os.path.join(output_dir, "elevation_srtm.npy")
    np.save(slope_path, slope_deg)
    np.save(elev_path,  elevation)
    print(f"\n  Slope grid saved:     {slope_path}")
    print(f"  Elevation grid saved: {elev_path}")

    # Visualise SRTM results
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        'Ouvahkelle Estate — Real Elevation and Slope\n'
        'Source: NASA SRTM 30m Resolution | Used by Component 3 Energy Model',
        fontsize=13, fontweight='bold'
    )

    im1 = axes[0].imshow(elevation, cmap='terrain')
    axes[0].set_title(
        f'Real Elevation (metres above sea level)\n'
        f'{valid.min():.0f}m to {valid.max():.0f}m  '
        f'(range: {valid.max()-valid.min():.0f}m)',
        fontsize=11
    )
    axes[0].set_xlabel('East →')
    axes[0].set_ylabel('North ↑')
    plt.colorbar(im1, ax=axes[0], label='Elevation (m above sea level)')

    im2 = axes[1].imshow(slope_deg, cmap='RdYlGn_r', vmin=0, vmax=45)
    axes[1].set_title(
        f'Real Slope (degrees) — Energy Model Input\n'
        f'Average: {valid_slope.mean():.1f}°  |  '
        f'Steep (>20°): {(valid_slope>=20).mean()*100:.1f}%',
        fontsize=11
    )
    axes[1].set_xlabel('East →')
    axes[1].set_ylabel('North ↑')
    plt.colorbar(im2, ax=axes[1], label='Slope (degrees)')
    axes[1].text(
        0.02, 0.98,
        f'Green = flat (0-5°): {(valid_slope<5).mean()*100:.1f}%\n'
        f'Yellow = moderate (5-20°): {((valid_slope>=5)&(valid_slope<20)).mean()*100:.1f}%\n'
        f'Red = steep (>20°): {(valid_slope>=20).mean()*100:.1f}%',
        transform=axes[1].transAxes, fontsize=9,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9)
    )

    viz_path = os.path.join(output_dir, "srtm_analysis.png")
    plt.tight_layout()
    plt.savefig(viz_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  Visualisation saved:  {viz_path}")

    return slope_deg, elevation


def main():
    BASE      = os.path.expanduser("~/component3")
    TIFF_PATH = f"{BASE}/terrain/result.tif"
    SRTM_PATH = f"{BASE}/terrain/srtm/srtm_53_11.tif"
    KML_PATH  = f"{BASE}/terrain/result.kml"
    HEIGHTMAP = f"{BASE}/terrain/heightmap.png"
    ORTHO_VIZ = f"{BASE}/terrain/orthophoto_analysis.png"

    print("=" * 60)
    print("Component 3 — Terrain Processor")
    print("Kenilworth International — Ouvahkelle Estate")
    print("=" * 60)
    print("\nTwo data sources:")
    print("  1. Kenilworth orthophoto → Gazebo visual terrain")
    print("  2. NASA SRTM elevation  → Energy model slope grid")

    # ── Part 1: Orthophoto for Gazebo visual ──
    if os.path.exists(TIFF_PATH):
        process_orthophoto(TIFF_PATH, HEIGHTMAP, ORTHO_VIZ)
    else:
        print(f"\nERROR: Orthophoto not found: {TIFF_PATH}")

    # ── Part 2: SRTM for real elevation and slope ──
    if os.path.exists(SRTM_PATH):
        slope_deg, elevation = process_srtm(
            SRTM_PATH, KML_PATH, f"{BASE}/terrain"
        )
    else:
        print(f"\nERROR: SRTM file not found: {SRTM_PATH}")

    print("\n" + "=" * 60)
    print("TERRAIN PROCESSING COMPLETE")
    print(f"  Heightmap (Gazebo):   {HEIGHTMAP}")
    print(f"  Orthophoto analysis:  {ORTHO_VIZ}")
    print(f"  SRTM slope grid:      {BASE}/terrain/slope_grid_srtm.npy")
    print(f"  SRTM elevation:       {BASE}/terrain/elevation_srtm.npy")
    print(f"  SRTM analysis:        {BASE}/terrain/srtm_analysis.png")
    print("=" * 60)


if __name__ == "__main__":
    main()