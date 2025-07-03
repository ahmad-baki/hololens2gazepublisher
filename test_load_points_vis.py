#!/usr/bin/env python3
"""
Point cloud viewer: loads a PNG for color and a text file for the point cloud,
then visualizes in 3D using Open3D.
"""
import sys
import argparse
import numpy as np
import cv2
import open3d as o3d

def load_color_image(path, ispng=False):
    if not ispng and not path.endswith('.png'):
        try:
            img = np.load(path)
        except Exception as e:
            sys.exit(f"Error: Could not load color array from '{path}': {e}")
        if img.ndim != 3 or img.shape[2] not in (3, 4):
            sys.exit(f"Error: Color array must be HxWx3 or HxWx4, got shape {img.shape}")
        # If RGBA, drop alpha
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img.astype(np.uint8)
    elif ispng or path.endswith('.png'):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            sys.exit(f"Error: Could not load color image from '{path}'")
        if img.ndim != 3 or img.shape[2] not in (3, 4):
            sys.exit(f"Error: Color image must be HxWx3 or HxWx4, got shape {img.shape}")
        # If RGBA, drop alpha
        if img.shape[2] == 4:
            img = img[:, :, :3]
        return img.astype(np.uint8)

def load_point_cloud(path):
    try:
        pts = np.loadtxt(path, dtype=np.float64)
    except Exception as e:
        sys.exit(f"Error: Could not load point cloud from '{path}': {e}")
    if pts.ndim != 2 or pts.shape[1] != 3:
        sys.exit(f"Error: Point cloud file must have Nx3 columns, got shape {pts.shape}")
    return pts

def center_view(vis):
    vis.reset_view_point(True)
    
def main():
    # parser = argparse.ArgumentParser(description="3D point cloud viewer using Open3D")
    # parser.add_argument('--color', '-c', required=True, help="Path to the color PNG image")
    # parser.add_argument('--points', '-p', required=True, help="Path to the point cloud text file (Nx3)")
    # args = parser.parse_args()
    # color_path = args.color
    # point_path = args.points

    color_path = "/home/abaki/Desktop/hololens2gazepublisher/data/test/2025_07_03-09_59_15/sensors/side_cam/0.png"
    point_path = "/home/abaki/Desktop/hololens2gazepublisher/data/test/2025_07_03-09_59_15/sensors/side_cam/0.txt"

    color_rgb = load_color_image(color_path)
    points = load_point_cloud(point_path)

    # Flatten color to Nx3
    h, w, _ = color_rgb.shape
    colors_flat = color_rgb.reshape(-1, 3) / 255.0
    if colors_flat.shape[0] != points.shape[0]:
        print(f"Warning: Number of colors ({colors_flat.shape[0]}) does not match number of points ({points.shape[0]}). Truncating to min length.")
        min_n = min(colors_flat.shape[0], points.shape[0])
        colors_flat = colors_flat[:min_n]
        points = points[:min_n]

    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors_flat)

    # Visualization
    vis = o3d.visualization.VisualizerWithKeyCallback()
    vis.create_window(window_name="Point Cloud Viewer")
    # Add coordinate frame
    coord = o3d.geometry.TriangleMesh.create_coordinate_frame(size=1.0)
    vis.add_geometry(coord)
    vis.add_geometry(pcd)

    # Close on Q key
    vis.register_key_callback(ord('Q'), lambda vis: vis.close())
    vis.register_key_callback(ord("C"), center_view)

    vis.run()
    vis.destroy_window()

if __name__ == "__main__":
    main()
