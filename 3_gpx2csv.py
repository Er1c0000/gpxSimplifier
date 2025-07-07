import os
import gpxpy
import csv

# 遍历目录，转换 GPX 文件为 CSV 的函数
def convert_gpx_to_csv(root_dir):
    # 目标 CSV 根目录
    csv_root = os.path.join(root_dir, "csv")
    os.makedirs(csv_root, exist_ok=True)
    
    # 遍历目录
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 跳过 csv 文件夹本身，避免重复处理
        if "csv" in dirpath.split(os.sep):
            continue
        for filename in filenames:
            if filename.endswith(".gpx"):
                gpx_file_path = os.path.join(dirpath, filename)
                print(f"正在读取文件: {gpx_file_path}")  # 输出正在读取的文件信息
                # 构建对应的 CSV 存储路径
                relative_path = os.path.relpath(dirpath, root_dir)
                csv_dir = os.path.join(csv_root, relative_path)
                os.makedirs(csv_dir, exist_ok=True)
                csv_file_path = os.path.join(csv_dir, filename.replace(".gpx", ".csv"))
                
                # 解析 GPX 文件并写入 CSV
                try:
                    with open(gpx_file_path, 'r', encoding='utf-8') as gpx_f:
                        gpx = gpxpy.parse(gpx_f)
                        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_f:
                            writer = csv.writer(csv_f)
                            # 写入表头，可根据 GPX 实际包含信息调整，这里示例写经纬度、时间
                            writer.writerow(["Latitude", "Longitude", "Time"])
                            for track in gpx.tracks:
                                for segment in track.segments:
                                    for point in segment.points:
                                        writer.writerow([point.latitude, point.longitude, point.time])
                    print(f"    成功转换为: {csv_file_path}")  # 输出成功转换的文件信息
                except Exception as e:
                    print(f"处理文件 {gpx_file_path} 时出错: {e}")

if __name__ == "__main__":
    # 当前脚本所在目录，可根据实际情况修改为要处理的根目录
    root_directory = os.path.dirname(os.path.abspath(__file__))  
    convert_gpx_to_csv(root_directory)