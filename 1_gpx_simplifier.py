import xml.etree.ElementTree as ET
from math import radians, cos, sin, asin, sqrt
from datetime import datetime
import numpy as np
from collections import defaultdict
import os

class GPXSimplifier:
    def __init__(self, stay_radius=100, min_stay_time=600, max_stay_points=2, moving_threshold=200):
        """
        初始化GPX简化器
        
        Args:
            stay_radius: 判定为同一停留区域的半径（米）
            min_stay_time: 最小停留时间（秒），低于此时间不认为是停留
            max_stay_points: 每个停留区域保留的最大点数
            moving_threshold: 判定为移动的最小距离（米）
        """
        self.stay_radius = stay_radius
        self.min_stay_time = min_stay_time
        self.max_stay_points = max_stay_points
        self.moving_threshold = moving_threshold
        
        # 定义北京邮电大学区域 (西北, 东北, 西南, 东南)
        # BUPT bounding box: (min_lon, max_lon, min_lat, max_lat)
        self.bupt_area = {
            'min_lat': 39.95822855, # 东南的纬度
            'max_lat': 39.96502929, # 东北的纬度
            'min_lon': 116.35502636, # 西北的经度
            'max_lon': 116.36105597  # 东南的经度
        }
        self.bupt_simplified_points_count = 2 # 在BUPT区域内保留的点数

    def is_in_bupt_area(self, lat, lon):
        """检查点是否在北京邮电大学区域内"""
        return (self.bupt_area['min_lat'] <= lat <= self.bupt_area['max_lat'] and
                self.bupt_area['min_lon'] <= lon <= self.bupt_area['max_lon'])

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        """计算两点间的距离（米）"""
        # 转换为弧度
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # haversine公式
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # 地球半径（米）
        r = 6371000
        return c * r
    
    def parse_gpx(self, file_path):
        """解析GPX文件"""
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print(f"GPX根元素: {root.tag}")
        print(f"GPX命名空间: {root.nsmap if hasattr(root, 'nsmap') else '无'}")
        
        # 获取所有可能的命名空间
        namespaces = {}
        if root.tag.startswith('{'):
            # 提取默认命名空间
            ns_end = root.tag.find('}')
            default_ns = root.tag[1:ns_end]
            namespaces['gpx'] = default_ns
        
        points = []
        
        # 尝试多种方式查找轨迹点
        trkpts = []
        
        # 方法1: 使用命名空间
        if namespaces:
            trkpts = root.findall('.//gpx:trkpt', namespaces)
            print(f"使用命名空间找到 {len(trkpts)} 个轨迹点")
        
        # 方法2: 不使用命名空间
        if not trkpts:
            trkpts = root.findall('.//trkpt')
            print(f"不使用命名空间找到 {len(trkpts)} 个轨迹点")
        
        # 方法3: 查找所有包含lat和lon属性的元素
        if not trkpts:
            for elem in root.iter():
                if elem.get('lat') and elem.get('lon'):
                    trkpts.append(elem)
            print(f"通过属性匹配找到 {len(trkpts)} 个轨迹点")
        
        # 方法4: 调试 - 打印GPX结构
        if not trkpts:
            print("未找到轨迹点，打印GPX结构前10个元素:")
            count = 0
            for elem in root.iter():
                print(f"  {elem.tag}: {elem.attrib}")
                count += 1
                if count >= 10:
                    break
        
        for trkpt in trkpts:
            try:
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                
                # 获取时间
                time_elem = None
                timestamp = None
                
                # 尝试不同的时间元素查找方式
                if namespaces:
                    time_elem = trkpt.find('gpx:time', namespaces)
                if time_elem is None:
                    time_elem = trkpt.find('time')
                
                if time_elem is not None and time_elem.text:
                    time_str = time_elem.text.strip()
                    # 解析时间（处理不同格式）
                    try:
                        if 'T' in time_str:
                            if time_str.endswith('Z'):
                                timestamp = datetime.fromisoformat(time_str[:-1].replace('Z', ''))
                            elif '+' in time_str or time_str.count(':') > 2:
                                # 处理带时区的时间
                                timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            else:
                                timestamp = datetime.fromisoformat(time_str)
                        else:
                            timestamp = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        print(f"时间解析失败: {time_str}, 错误: {e}")
                        timestamp = None
                
                points.append({
                    'lat': lat,
                    'lon': lon,
                    'time': timestamp,
                    'element': trkpt
                })
            except (ValueError, TypeError) as e:
                print(f"解析轨迹点失败: {e}")
                continue
        
        print(f"成功解析 {len(points)} 个轨迹点")
        return points, tree, root, namespaces
    
    def identify_stay_areas_improved(self, points):
        """改进的停留区域识别算法"""
        if not points:
            return [], []
        
        # 使用滑动窗口和聚类方法识别停留区域
        stay_areas = []
        moving_segments = []
        
        i = 0
        while i < len(points):
            current_point = points[i]
            potential_stay_area = [current_point]
            
            # 向前查找可能属于同一停留区域的点
            j = i + 1
            while j < len(points):
                next_point = points[j]
                
                # 计算与停留区域中心的距离
                center_lat = sum(p['lat'] for p in potential_stay_area) / len(potential_stay_area)
                center_lon = sum(p['lon'] for p in potential_stay_area) / len(potential_stay_area)
                
                distance = self.haversine_distance(
                    next_point['lat'], next_point['lon'], center_lat, center_lon
                )
                
                if distance <= self.stay_radius:
                    potential_stay_area.append(next_point)
                    j += 1
                else:
                    # 检查是否是短暂移动后又回到停留区域
                    temp_moving = []
                    k = j
                    while k < len(points) and len(temp_moving) < 10:  # 最多检查10个点
                        temp_point = points[k]
                        temp_distance = self.haversine_distance(
                            temp_point['lat'], temp_point['lon'], center_lat, center_lon
                        )
                        
                        if temp_distance <= self.stay_radius:
                            # 回到了停留区域，将临时移动的点也加入
                            potential_stay_area.extend(temp_moving)
                            potential_stay_area.append(temp_point)
                            j = k + 1
                            break
                        else:
                            temp_moving.append(temp_point)
                            k += 1
                    else:
                        # 没有回到停留区域
                        break
            
            # 判断是否为有效的停留区域
            if self.is_stay_area(potential_stay_area):
                stay_areas.append(potential_stay_area)
                i = j
            else:
                # 不是停留区域，找到下一个移动段的终点
                moving_start = i
                while i < len(points) - 1:
                    current = points[i]
                    next_pt = points[i + 1]
                    distance = self.haversine_distance(
                        current['lat'], current['lon'], next_pt['lat'], next_pt['lon']
                    )
                    
                    # 如果距离很小，可能是开始停留了
                    if distance < 10:  # 10米以内认为开始可能停留
                        break
                    i += 1
                
                if i > moving_start:
                    moving_segments.append(points[moving_start:i+1])
                i += 1
        
        return stay_areas, moving_segments
    
    def simplify_gpx_improved(self, input_file, output_file):
        """改进的GPX简化方法"""
        points, tree, root, ns = self.parse_gpx(input_file)
        print(f"原始点数: {len(points)}")
        
        if len(points) == 0:
            print("错误: 没有找到任何轨迹点，请检查GPX文件格式")
            return
        
        # ---- 新增的BUPT区域预处理逻辑 ----
        print("开始BUPT区域预处理...")
        processed_points = []
        bupt_cluster = []
        
        for point in points:
            if self.is_in_bupt_area(point['lat'], point['lon']):
                bupt_cluster.append(point)
            else:
                if bupt_cluster:
                    # 如果前面有BUPT区域的点，先简化它们再添加到processed_points
                    simplified_bupt = self._simplify_bupt_cluster(bupt_cluster)
                    processed_points.extend(simplified_bupt)
                    bupt_cluster = [] # 重置BUPT集群
                processed_points.append(point)
        
        # 处理可能在文件末尾的BUPT集群
        if bupt_cluster:
            simplified_bupt = self._simplify_bupt_cluster(bupt_cluster)
            processed_points.extend(simplified_bupt)
        
        print(f"BUPT区域预处理后点数: {len(processed_points)}")
        points = processed_points
        # ---- BUPT区域预处理逻辑结束 ----

        # 使用改进的识别算法
        stay_areas, moving_segments = self.identify_stay_areas_improved(points)
        print(f"识别到 {len(stay_areas)} 个停留区域")
        print(f"识别到 {len(moving_segments)} 个移动段")
        
        simplified_points = []
        
        # 标记所有停留区域的点
        stay_points_set = set()
        for area in stay_areas:
            for point in area:
                stay_points_set.add(id(point))
        
        # 处理每个点
        # 注意：这里需要确保被_source_area标记的点不会被重复处理
        processed_areas = set() 
        for point in points:
            if id(point) in stay_points_set:
                # 这个点属于停留区域，检查是否已经处理过这个区域
                for area in stay_areas:
                    # 使用id(area[0])作为区域的唯一标识
                    if point in area and id(area[0]) not in processed_areas: 
                        # 简化这个停留区域（只处理一次）
                        simplified_area = self.simplify_stay_area(area)
                        simplified_points.extend(simplified_area)
                        processed_areas.add(id(area[0])) # 标记为已处理
                        print(f"停留区域: {len(area)} 点简化为 {len(simplified_area)} 点")
                        break
            else:
                # 不在停留区域的点，检查是否需要保留
                if self.should_keep_moving_point(point, points, simplified_points):
                    simplified_points.append(point)
        
        # 按时间排序（如果有时间信息）
        if simplified_points and simplified_points[0]['time']:
            simplified_points.sort(key=lambda p: p['time'] or datetime.min)
        
        print(f"简化后点数: {len(simplified_points)}")
        
        # 创建新的GPX文件
        self.create_simplified_gpx(simplified_points, tree, root, ns, output_file)

    def _simplify_bupt_cluster(self, bupt_cluster):
        """
        对BUPT区域内的点进行大幅度缩减。
        根据 self.bupt_simplified_points_count 决定保留点数。
        """
        if not bupt_cluster:
            return []
        
        if len(bupt_cluster) <= self.bupt_simplified_points_count:
            return bupt_cluster
        
        simplified = []
        if self.bupt_simplified_points_count >= 1:
            simplified.append(bupt_cluster[0]) # 保留第一个点
        
        if self.bupt_simplified_points_count >= 2:
            # 如果有时间，保留最早和最晚
            if bupt_cluster[0]['time'] and bupt_cluster[-1]['time']:
                sorted_cluster = sorted(bupt_cluster, key=lambda p: p['time'])
                if sorted_cluster[0] not in simplified:
                    simplified.append(sorted_cluster[0])
                if sorted_cluster[-1] not in simplified:
                    simplified.append(sorted_cluster[-1])
            else: # 如果没有时间，保留第一个和最后一个
                if bupt_cluster[-1] not in simplified:
                    simplified.append(bupt_cluster[-1])
        
        if self.bupt_simplified_points_count >= 3:
            # 如果需要更多点，可以考虑保留一个中心点
            center_lat = sum(p['lat'] for p in bupt_cluster) / len(bupt_cluster)
            center_lon = sum(p['lon'] for p in bupt_cluster) / len(bupt_cluster)
            
            min_distance = float('inf')
            central_point = None
            for point in bupt_cluster:
                distance = self.haversine_distance(
                    point['lat'], point['lon'], center_lat, center_lon
                )
                if distance < min_distance and point not in simplified:
                    min_distance = distance
                    central_point = point
            if central_point:
                simplified.append(central_point)
        
        # 确保最终返回的点数不超过设定值，并保持唯一性
        final_simplified = []
        seen_ids = set()
        for p in simplified:
            if id(p) not in seen_ids:
                final_simplified.append(p)
                seen_ids.add(id(p))

        # 如果简化后的点不够数量，从原集群中按时间顺序补充
        if len(final_simplified) < self.bupt_simplified_points_count:
            remaining_points = [p for p in bupt_cluster if id(p) not in seen_ids]
            if remaining_points:
                remaining_points.sort(key=lambda p: p['time'] or datetime.min)
                final_simplified.extend(remaining_points[:self.bupt_simplified_points_count - len(final_simplified)])

        # 确保按时间排序
        if final_simplified and final_simplified[0]['time']:
            final_simplified.sort(key=lambda p: p['time'] or datetime.min)

        print(f"BUPT集群 ({len(bupt_cluster)}点) 简化为 {len(final_simplified)}点")
        return final_simplified

    
    def should_keep_moving_point(self, point, all_points, simplified_points):
        """判断移动点是否应该保留"""
        # 如果是BUPT区域预处理后的点，并且已经处理过，就不再保留
        # 这个逻辑在新的简化流程中可能不再必要，因为BUPT点已经预处理并纳入 simplified_points
        # 并且id(point) in stay_points_set 会处理停留点。
        # 这里的判断主要是针对非停留区域的移动点
        
        if not simplified_points:
            return True
        
        # 计算与最后一个简化点的距离
        last_point = simplified_points[-1]
        distance = self.haversine_distance(
            point['lat'], point['lon'], last_point['lat'], last_point['lon']
        )
        
        # 如果距离足够大，保留这个点
        if distance >= self.moving_threshold:
            return True
        
        # 如果是轨迹的关键转折点，也要保留
        # point_index 是 point 在原始 all_points 中的索引，但现在 all_points 是预处理后的点
        # 需要找到 point 在当前 points 列表中的索引
        try:
            point_index = next((i for i, p in enumerate(all_points) if p is point), -1)
            if self.is_turning_point(point, all_points, point_index):
                return True
        except Exception as e:
            # 调试信息，如果找不到索引或者is_turning_point出错
            print(f"Error checking turning point for {point}: {e}")
            pass
        
        return False
    
    def is_turning_point(self, point, all_points, point_index, window=5):
        """判断是否为轨迹转折点"""
        if point_index < 0 or point_index >= len(all_points): # 确保索引有效
            return False

        # 如果点在处理后的列表中的位置不适合计算窗口，则保留
        if point_index < window or point_index >= len(all_points) - window:
            return True  # 端点保留
        
        # 计算前后方向向量的角度变化
        try:
            prev_point = all_points[point_index - window]
            next_point = all_points[point_index + window]
            
            # 简单的角度变化检测
            bearing1 = self.calculate_bearing(prev_point, point)
            bearing2 = self.calculate_bearing(point, next_point)
            
            angle_diff = abs(bearing1 - bearing2)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            
            # 如果方向变化超过30度，认为是转折点
            return angle_diff > 30
        except Exception as e:
            # 确保即使出现错误也不会崩溃
            print(f"Error calculating turning point: {e}")
            return False
    
    def calculate_bearing(self, point1, point2):
        """计算两点间的方位角"""
        # 检查是否是同一个点，避免除以零
        if point1['lat'] == point2['lat'] and point1['lon'] == point2['lon']:
            return 0.0 # 或者其他约定值
            
        lat1, lon1 = radians(point1['lat']), radians(point1['lon'])
        lat2, lon2 = radians(point2['lat']), radians(point2['lon'])
        
        dlon = lon2 - lon1
        
        y = sin(dlon) * cos(lat2)
        x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        
        bearing = np.arctan2(y, x)
        return np.degrees(bearing)
    
    def is_stay_area(self, area_points):
        """判断是否为停留区域"""
        if len(area_points) < 2:
            return False
        
        # 如果有时间信息，检查停留时间
        if area_points[0]['time'] and area_points[-1]['time']:
            stay_duration = (area_points[-1]['time'] - area_points[0]['time']).total_seconds()
            return stay_duration >= self.min_stay_time
        
        # 如果没有时间信息，根据点数判断（假设采样频率固定）
        return len(area_points) >= 10  # 可调整这个阈值
    
    def simplify_stay_area(self, area_points):
        """简化停留区域的点 - 更激进的简化策略"""
        if len(area_points) <= self.max_stay_points:
            return area_points
        
        if self.max_stay_points == 1:
            # 只保留中心点
            center_lat = sum(p['lat'] for p in area_points) / len(area_points)
            center_lon = sum(p['lon'] for p in area_points) / len(area_points)
            
            # 找到最接近中心的点
            min_distance = float('inf')
            center_point = area_points[0]
            for point in area_points:
                distance = self.haversine_distance(
                    point['lat'], point['lon'], center_lat, center_lon
                )
                if distance < min_distance:
                    min_distance = distance
                    center_point = point
            
            return [center_point]
        
        elif self.max_stay_points == 2:
            # 保留第一个和最后一个点
            return [area_points[0], area_points[-1]]
        
        else:
            # 保留第一个点、最后一个点，以及中间的关键点
            simplified = [area_points[0]]  # 起始点
            
            if self.max_stay_points > 2:
                # 在中间点中均匀选择，但更少
                middle_count = min(self.max_stay_points - 2, 1)  # 中间最多1个点
                if middle_count > 0:
                    middle_index = len(area_points) // 2
                    simplified.append(area_points[middle_index])
            
            simplified.append(area_points[-1])  # 结束点
            
            # 确保不重复添加
            final_simplified = []
            seen_ids = set()
            for p in simplified:
                if id(p) not in seen_ids:
                    final_simplified.append(p)
                    seen_ids.add(id(p))
            
            return final_simplified
    
    def simplify_gpx(self, input_file, output_file):
        """简化GPX文件 - 这个方法在最新的修改中实际上被 simplify_gpx_improved 替代了，但为了兼容性保留"""
        # 为了集成BUPT处理，我们主要使用simplify_gpx_improved
        # 理论上可以把BUPT处理逻辑也放到这里，但为了清晰性，我选择在_improved版本中进行修改。
        # 如果只调用 simplify_gpx，它会缺失BUPT预处理。
        # 因此，推荐外部调用 simplify_gpx_improved。
        
        # 实际上，这里可以简单地调用 simplify_gpx_improved
        self.simplify_gpx_improved(input_file, output_file)
    
    def create_simplified_gpx(self, points, original_tree, original_root, ns, output_file):
        """创建简化后的GPX文件"""
        # 创建新的GPX结构
        new_root = ET.Element('gpx')
        new_root.set('version', '1.1')
        new_root.set('creator', 'GPX Simplifier') # 更新creator信息
        
        # 添加命名空间
        if ns.get('gpx'):
            new_root.set('xmlns', ns['gpx'])
        
        # 创建轨迹
        trk = ET.SubElement(new_root, 'trk')
        trk_name = ET.SubElement(trk, 'name')
        trk_name.text = 'Simplified Track' # 更新轨迹名称
        
        trkseg = ET.SubElement(trk, 'trkseg')
        
        # 添加简化后的点
        for point in points:
            trkpt = ET.SubElement(trkseg, 'trkpt')
            trkpt.set('lat', str(point['lat']))
            trkpt.set('lon', str(point['lon']))
            
            if point['time']:
                time_elem = ET.SubElement(trkpt, 'time')
                time_elem.text = point['time'].isoformat() + 'Z'
        
        # 写入文件
        tree = ET.ElementTree(new_root)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        print(f"简化后的GPX文件已保存到: {output_file}")

# 使用示例
def main():
    # 创建简化器实例
    simplifier = GPXSimplifier(
        stay_radius=50,        # 50米范围内认为是同一位置
        min_stay_time=300,     # 停留5分钟以上才算停留区域
        max_stay_points=3      # 每个停留区域最多保留3个点
    )
    
    original_folder = 'Original'
    simplified_folder = 'Simplified' # 新的文件夹名
    
    # 确保Simplified文件夹存在
    if not os.path.exists(simplified_folder):
        os.makedirs(simplified_folder)
    
    # 遍历Original文件夹中的所有GPX文件
    for filename in os.listdir(original_folder):
        if filename.endswith('.gpx'):
            input_file = os.path.join(original_folder, filename)
            base_name = os.path.splitext(filename)[0]
            output_file = os.path.join(simplified_folder, f'{base_name}_simplified.gpx') # 新的文件名后缀
            
            try:
                print(f"开始处理文件: {input_file}")
                # 调用改进的简化方法
                simplifier.simplify_gpx_improved(input_file, output_file)
            except FileNotFoundError:
                print(f"文件 {input_file} 不存在，请检查文件路径")
            except ET.ParseError as e:
                print(f"GPX文件格式错误: {e}")
                print("请确保文件是有效的GPX格式")
            except Exception as e:
                print(f"处理过程中出现错误: {e}")
                import traceback
                traceback.print_exc()

def check_gpx_file(file_path):
    """检查GPX文件的基本信息"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        print(f"=== GPX文件信息 ===")
        print(f"文件: {file_path}")
        print(f"根元素: {root.tag}")
        print(f"根元素属性: {root.attrib}")
        
        # 统计各种元素
        all_elements = list(root.iter())
        print(f"总元素数: {len(all_elements)}")
        
        # 统计不同类型的元素
        element_count = {}
        for elem in all_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            element_count[tag] = element_count.get(tag, 0) + 1
        
        print("元素统计:")
        for tag, count in sorted(element_count.items()):
            print(f"  {tag}: {count}")
        
        # 查找轨迹点
        trkpts = []
        for elem in root.iter():
            if elem.get('lat') and elem.get('lon'):
                trkpts.append(elem)
        
        print(f"找到 {len(trkpts)} 个轨迹点")
        
        if trkpts:
            first_point = trkpts[0]
            print(f"第一个轨迹点: lat={first_point.get('lat')}, lon={first_point.get('lon')}")
            
            # 检查时间信息
            time_elem = first_point.find('time') or first_point.find('.//*[local-name()="time"]')
            if time_elem is not None:
                print(f"时间信息: {time_elem.text}")
            else:
                print("无时间信息")
    
    except Exception as e:
        print(f"检查文件时出错: {e}")

if __name__ == "__main__":
    # 如果要检查GPX文件信息，取消下面这行的注释
    # check_gpx_file('input.gpx')
    
    main()