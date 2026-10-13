# terrain_processor.py
# Component 3 — Terrain Processing Module
# Reads a windowed section of the large Kenilworth GeoTIFF
# to avoid memory issues with the full 34GB file
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
import rasterio
from rasterio.windows import Window

def get_tiff_info(tiff_path):
    """Print information about the TIFF file without loading it fully."""
    print(f"Reading TIFF info: {tiff_path}")
    with rasterio.open(tiff_path) as ds:
        print(f"  Full size:     {ds.width} x {ds.height} pixels")
        print(f"  Bands:         {ds.count}")
        print(f"  CRS:           {ds.crs}")
        print(f"  Bounds:        {ds.bounds}")
        transform = ds.transform
        pixel_size_deg = abs(transform.a)
        pixel_size_m = pixel_size_deg * 111320
        print(f"  Pixel size:    {pixel_size_deg:.8f} deg = {pixel_size_m:.4f} m")
        return ds.width, ds.height, pixel_size_m, ds.bounds


def find_estate_window(tiff_path):
    """
    Find the window that contains the actual estate data
    by looking for the region with most valid (non-zero, non-black) pixels.
    Samples at low resolution to avoid memory issues.
    """
    print(f"\nFinding estate window (sampling at low resolution)...")

    with rasterio.open(tiff_path) as ds:
        step = 50
        w = ds.width  // step
        h = ds.height // step

        # Read band 1 downsampled
        data = ds.read(
            1,
            out_shape=(h, w),
            resampling=rasterio.enums.Resampling.average
        ).astype(np.float32)

        print(f"  Overview size: {w} x {h} pixels")

        # Mark empty/no-data pixels
        data[data <= 0] = np.nan

        # Sliding window — find region with most valid data AND highest variation
        win = 20  # 20 overview pixels = 1000 real pixels
        best_score = 0
        best_row, best_col = 0, 0

        for r in range(0, h - win, 2):
            for c in range(0, w - win, 2):
                patch = data[r:r+win, c:c+win]
                valid = patch[~np.isnan(patch)]
                coverage = len(valid) / (win * win)

                if coverage > 0.7:  # at least 70% valid pixels
                    variation = float(valid.max() - valid.min())
                    score = coverage * variation
                    if score > best_score:
                        best_score = score
                        best_row, best_col = r, c

        # Convert overview coordinates back to full resolution
        real_col = best_col * step
        real_row = best_row * step
        real_width  = win * step
        real_height = win * step

        print(f"  Estate window at pixel ({real_col}, {real_row})")
        print(f"  Window size: {real_width} x {real_height} pixels")
        print(f"  Score (coverage x variation): {best_score:.1f}")

        return real_col, real_row, real_width, real_height


def load_tiff_window(tiff_path, col_off, row_off, width, height):
    """
    Load a specific window of the TIFF.
    Returns elevation array and pixel size in metres.
    """
    print(f"\nLoading window from TIFF...")
    print(f"  Position: ({col_off}, {row_off})")
    print(f"  Size:     {width} x {height} pixels")

    with rasterio.open(tiff_path) as ds:
        pixel_size_deg = abs(ds.transform.a)
        pixel_size_m   = pixel_size_deg * 111320

        # Clamp to file bounds
        width  = min(width,  ds.width  - col_off)
        height = min(height, ds.height - row_off)

        window    = Window(col_off, row_off, width, height)
        elevation = ds.read(1, window=window).astype(np.float32)

    # Mark empty pixels as NaN
    elevation[elevation <= 0] = np.nan

    valid = elevation[~np.isnan(elevation)]
    if len(valid) == 0:
        print("  ERROR: No valid data in this window.")
        return None, pixel_size_m

    print(f"  Loaded size:       {elevation.shape}")
    print(f"  Valid pixels:      {len(valid):,} of {elevation.size:,} "
          f"({len(valid)/elevation.size*100:.1f}%)")
    print(f"  Pixel value min:   {valid.min():.1f}")
    print(f"  Pixel value max:   {valid.max():.1f}")
    print(f"  Value range:       {valid.max() - valid.min():.1f}")

    return elevation, pixel_size_m


def generate_heightmap(elevation, output_path, target_size=513):
    """
    Generate a Gazebo-compatible greyscale heightmap PNG.
    Gazebo requires size = 2^n + 1: 129, 257, 513, 1025
    """
    print(f"\nGenerating heightmap ({target_size} x {target_size})...")

    valid    = elevation[~np.isnan(elevation)]
    elev_min = valid.min()
    elev_max = valid.max()

    # Fill NaN with minimum value
    elev_filled = np.where(np.isnan(elevation), elev_min, elevation)

    # Normalise to 0-255
    if elev_max > elev_min:
        normalised = ((elev_filled - elev_min) / (elev_max - elev_min) * 255)
    else:
        normalised = np.zeros_like(elev_filled)

    normalised = np.clip(normalised, 0, 255).astype(np.uint8)

    # Resize to target
    img         = Image.fromarray(normalised, mode='L')
    img_resized = img.resize((target_size, target_size), Image.LANCZOS)
    img_resized.save(output_path)

    # Save metadata for Gazebo world file generation
    metadata = {
        "heightmap_size_pixels": target_size,
        "pixel_value_min":       float(elev_min),
        "pixel_value_max":       float(elev_max),
        "pixel_value_range":     float(elev_max - elev_min),
        "gazebo_world_size_m":   500,
        "gazebo_height_scale_m": 80,
        "heightmap_file":        output_path,
        "note": "This is an orthophoto TIFF. Pixel values are RGB intensity, not metres. "
                "Elevation in metres estimated from SULEKO flight data (890-1240m range for Hatton)."
    }
    meta_path = output_path.replace('.png', '_metadata.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"  Heightmap saved:  {output_path}")
    print(f"  Metadata saved:   {meta_path}")

    return elev_min, elev_max


def compute_slope_grid(elevation, pixel_size_m, output_path):
    """
    Compute terrain slope in degrees at every pixel.
    NaN areas (outside estate) are excluded from statistics.
    """
    print(f"\nComputing slope grid...")
    print(f"  Pixel size: {pixel_size_m:.4f} m")

    # Fill NaN with nearest valid for gradient — but track mask
    valid_mask  = ~np.isnan(elevation)
    valid_min   = elevation[valid_mask].min()
    elev_filled = np.where(np.isnan(elevation), valid_min, elevation)

    # Compute gradient
    dz_dy, dz_dx = np.gradient(elev_filled, pixel_size_m)
    slope_rad     = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg     = np.degrees(slope_rad)

    # Set slope to NaN outside estate boundary
    slope_deg[~valid_mask] = np.nan

    # Save
    np.save(output_path, slope_deg)

    # Stats on valid area only
    valid_slope = slope_deg[~np.isnan(slope_deg)]
    print(f"  Saved:                 {output_path}")
    print(f"  Slope range:           {valid_slope.min():.1f} to {valid_slope.max():.1f} degrees")
    print(f"  Average slope:         {valid_slope.mean():.1f} degrees")
    print(f"  Flat  (0-5 deg):       {(valid_slope < 5).mean()*100:.1f}%")
    print(f"  Moderate (5-20 deg):   {((valid_slope>=5)&(valid_slope<20)).mean()*100:.1f}%")
    print(f"  Steep (>20 deg):       {(valid_slope>=20).mean()*100:.1f}%")

    return slope_deg


def visualise(elevation, slope_deg, output_path):
    """Generate terrain analysis visualisation for presentation."""
    print(f"\nGenerating visualisation...")

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        'Ouvahkelle Estate — Kenilworth International\n'
        'Terrain Analysis for Component 3 Navigation System',
        fontsize=14, fontweight='bold'
    )

    # --- Elevation map ---
    valid    = elevation[~np.isnan(elevation)]
    elev_min = valid.min()
    elev_max = valid.max()

    im1 = axes[0].imshow(
        elevation, cmap='terrain',
        vmin=elev_min, vmax=elev_max
    )
    axes[0].set_title(
        f'Orthophoto Band 1 (Elevation Proxy)\n'
        f'Value range: {elev_min:.0f} to {elev_max:.0f}  '
        f'(variation: {elev_max - elev_min:.0f})',
        fontsize=11
    )
    axes[0].set_xlabel('East →')
    axes[0].set_ylabel('North ↑')
    plt.colorbar(im1, ax=axes[0], label='Pixel value')

    # --- Slope map (valid area only) ---
    valid_slope = slope_deg[~np.isnan(slope_deg)]
    im2 = axes[1].imshow(
        slope_deg, cmap='RdYlGn_r',
        vmin=0, vmax=45
    )
    axes[1].set_title(
        f'Slope Map (estate area only)\n'
        f'Average: {valid_slope.mean():.1f}°  |  '
        f'Steep (>20°): {(valid_slope >= 20).mean()*100:.1f}%',
        fontsize=11
    )
    axes[1].set_xlabel('East →')
    axes[1].set_ylabel('North ↑')
    plt.colorbar(im2, ax=axes[1], label='Slope (degrees)')

    axes[1].text(
        0.02, 0.98,
        'Green = flat (0-5°)\nYellow = moderate (5-20°)\nRed = steep (>20°)\nWhite = outside estate',
        transform=axes[1].transAxes, fontsize=9,
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.9)
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  Saved: {output_path}")
    plt.close()


def main():
    BASE          = os.path.expanduser("~/component3")
    TIFF_PATH     = f"{BASE}/terrain/result.tif"
    HEIGHTMAP     = f"{BASE}/terrain/heightmap.png"
    SLOPE_GRID    = f"{BASE}/terrain/slope_grid.npy"
    VISUALISATION = f"{BASE}/terrain/terrain_analysis.png"

    print("=" * 60)
    print("Component 3 — Terrain Processor")
    print("Kenilworth International — Ouvahkelle Estate")
    print("=" * 60)

    if not os.path.exists(TIFF_PATH):
        print(f"\nERROR: File not found: {TIFF_PATH}")
        return

    # Step 1 — Get file info
    full_width, full_height, pixel_size_m, bounds = get_tiff_info(TIFF_PATH)

    # Step 2 — Find estate window automatically
    col_off, row_off, win_w, win_h = find_estate_window(TIFF_PATH)

    # Step 3 — Load that window
    elevation, pixel_size_m = load_tiff_window(
        TIFF_PATH, col_off, row_off, win_w, win_h
    )

    if elevation is None:
        print("ERROR: Could not load valid elevation data.")
        return

    # Step 4 — Generate Gazebo heightmap
    elev_min, elev_max = generate_heightmap(elevation, HEIGHTMAP)

    # Step 5 — Compute slope grid
    slope_deg = compute_slope_grid(elevation, pixel_size_m, SLOPE_GRID)

    # Step 6 — Visualise
    visualise(elevation, slope_deg, VISUALISATION)

    print("\n" + "=" * 60)
    print("TERRAIN PROCESSING COMPLETE")
    print(f"  Heightmap:   {HEIGHTMAP}")
    print(f"  Slope grid:  {SLOPE_GRID}")
    print(f"  Analysis:    {VISUALISATION}")
    print("=" * 60)


if __name__ == "__main__":
    main()