import os
import xml.etree.ElementTree as ET

def merge_gpx_files_with_counts(input_dir):
    """
    合并指定目录下所有GPX文件的轨迹数据到一个新的GPX文件，并统计点数。

    Args:
        input_dir (str): 包含GPX文件的输入目录。
    """
    output_subdir = os.path.join(input_dir, "all")
    output_filepath = os.path.join(output_subdir, "allData.gpx")

    # 创建输出子目录（如果不存在）
    os.makedirs(output_subdir, exist_ok=True)

    # 初始化一个新的GPX根元素
    gpx_namespace = "http://www.topografix.com/GPX/1/0"
    ET.register_namespace("", gpx_namespace) # 注册默认命名空间
    merged_gpx = ET.Element("{%s}gpx" % gpx_namespace, version="1.1", creator="GPX Merger Script")
    
    # 初始化一个<trk>元素和<trkseg>元素来存放所有轨迹点
    merged_trk = ET.SubElement(merged_gpx, "{%s}trk" % gpx_namespace)
    ET.SubElement(merged_trk, "{%s}name" % gpx_namespace).text = "Merged Track (All Files)"
    merged_trkseg = ET.SubElement(merged_trk, "{%s}trkseg" % gpx_namespace)

    gpx_files = [f for f in os.listdir(input_dir) if f.endswith('.gpx')]

    if not gpx_files:
        print(f"在目录 '{input_dir}' 中没有找到GPX文件。")
        return

    print(f"在目录 '{input_dir}' 中找到 {len(gpx_files)} 个GPX文件。\n")

    total_merged_points = 0
    
    for filename in gpx_files:
        filepath = os.path.join(input_dir, filename)
        file_point_count = 0
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # 遍历所有的<trkseg>并提取<trkpt>
            for trkseg in root.findall(".//{%s}trkseg" % gpx_namespace):
                for trkpt in trkseg.findall(".//{%s}trkpt" % gpx_namespace):
                    # 将轨迹点添加到合并的<trkseg>中
                    merged_trkseg.append(trkpt)
                    file_point_count += 1
            total_merged_points += file_point_count
            print(f"已处理文件: {filename} - 包含 {file_point_count} 个轨迹点。")
        except ET.ParseError as e:
            print(f"解析文件 '{filename}' 时出错: {e}")
        except Exception as e:
            print(f"处理文件 '{filename}' 时发生未知错误: {e}")

    # 将合并后的GPX数据写入文件
    tree = ET.ElementTree(merged_gpx)
    try:
        ET.indent(tree, space="  ", level=0) 
        tree.write(output_filepath, encoding="utf-8", xml_declaration=True)
        print(f"\n所有GPX文件已成功合并到: {output_filepath}")
        print(f"合并后的文件共包含 {total_merged_points} 个轨迹点。")
    except Exception as e:
        print(f"写入合并GPX文件时出错: {e}")

# 设置您的GPX文件所在的目录
current_directory = os.path.dirname(os.path.abspath(__file__)) # 获取脚本当前目录
gpx_input_directory = os.path.join(current_directory, "Simplified")
# gpx_input_directory = os.path.join(current_directory, "Original")


if __name__ == "__main__":
    merge_gpx_files_with_counts(gpx_input_directory)