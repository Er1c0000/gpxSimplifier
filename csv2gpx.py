#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import datetime
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring
# import argparse  # 不再需要命令行参数解析
import os

def timestamp_to_iso(timestamp):
    """将时间戳转换为ISO格式的时间字符串"""
    try:
        # 假设时间戳是秒级别的
        dt = datetime.datetime.fromtimestamp(int(timestamp), tz=datetime.timezone.utc)
        return dt.isoformat()
    except:
        # 如果是毫秒级别的时间戳，除以1000
        dt = datetime.datetime.fromtimestamp(int(timestamp)/1000, tz=datetime.timezone.utc)
        return dt.isoformat()

def create_gpx_from_csv(csv_file, output_file=None):
    """
    将CSV文件转换为GPX格式
    
    Args:
        csv_file: 输入的CSV文件路径
        output_file: 输出的GPX文件路径，如果为None则自动生成
    """
    
    if output_file is None:
        output_file = os.path.splitext(csv_file)[0] + '.gpx'
    
    # 创建GPX根元素
    gpx = Element('gpx')
    gpx.set('version', '1.1')
    gpx.set('creator', 'CSV to GPX Converter')
    gpx.set('xmlns', 'http://www.topografix.com/GPX/1/1')
    gpx.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    gpx.set('xsi:schemaLocation', 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd')
    
    # 添加metadata
    metadata = SubElement(gpx, 'metadata')
    name = SubElement(metadata, 'name')
    name.text = 'Track from CSV'
    time = SubElement(metadata, 'time')
    time.text = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 创建track
    trk = SubElement(gpx, 'trk')
    trk_name = SubElement(trk, 'name')
    trk_name.text = 'GPS Track'
    
    # 创建track segment
    trkseg = SubElement(trk, 'trkseg')
    
    # 读取CSV文件
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # 检查是否有必要的列
            required_columns = ['dataTime', 'longitude', 'latitude']
            if not all(col in reader.fieldnames for col in required_columns):
                print(f"警告: CSV文件缺少必要的列。需要: {required_columns}")
                print(f"实际列: {reader.fieldnames}")
                return False
            
            # 先读取所有数据到列表中
            all_rows = []
            for row in reader:
                try:
                    # 验证基本数据
                    timestamp = row['dataTime']
                    longitude = float(row['longitude'])
                    latitude = float(row['latitude'])
                    
                    # 添加到列表中
                    all_rows.append(row)
                    
                except (ValueError, KeyError) as e:
                    print(f"跳过无效行: {row} - 错误: {e}")
                    continue
            
            # 按时间戳排序
            print(f"读取到 {len(all_rows)} 个有效GPS点")
            print("正在按时间排序...")
            
            all_rows.sort(key=lambda x: int(x['dataTime']))
            
            print("排序完成，开始生成GPX轨迹...")
            
            point_count = 0
            for row in all_rows:
                try:
                    # 获取基本位置信息
                    timestamp = row['dataTime']
                    longitude = float(row['longitude'])
                    latitude = float(row['latitude'])
                    
                    # 创建track point
                    trkpt = SubElement(trkseg, 'trkpt')
                    trkpt.set('lat', str(latitude))
                    trkpt.set('lon', str(longitude))
                    
                    # 添加时间
                    if timestamp:
                        time_elem = SubElement(trkpt, 'time')
                        time_elem.text = timestamp_to_iso(timestamp)
                    
                    # 添加海拔信息（如果有）
                    if 'altitude' in row and row['altitude']:
                        try:
                            altitude = float(row['altitude'])
                            ele = SubElement(trkpt, 'ele')
                            ele.text = str(altitude)
                        except ValueError:
                            pass
                    
                    # 添加速度信息（如果有）
                    if 'speed' in row and row['speed']:
                        try:
                            speed = float(row['speed'])
                            if speed > 0:
                                extensions = SubElement(trkpt, 'extensions')
                                speed_elem = SubElement(extensions, 'speed')
                                speed_elem.text = str(speed)
                        except ValueError:
                            pass
                    
                    # 添加精度信息（如果有）
                    if 'accuracy' in row and row['accuracy']:
                        try:
                            accuracy = float(row['accuracy'])
                            if accuracy > 0:
                                if trkpt.find('extensions') is None:
                                    extensions = SubElement(trkpt, 'extensions')
                                else:
                                    extensions = trkpt.find('extensions')
                                hdop = SubElement(extensions, 'hdop')
                                hdop.text = str(accuracy)
                        except ValueError:
                            pass
                    
                    point_count += 1
                    
                except (ValueError, KeyError) as e:
                    print(f"处理排序后数据时出错: {row} - 错误: {e}")
                    continue
            
            print(f"成功处理了 {point_count} 个GPS点")
            
    except FileNotFoundError:
        print(f"错误: 找不到文件 {csv_file}")
        return False
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
        return False
    
    # 格式化XML并写入文件
    try:
        rough_string = tostring(gpx, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # 移除多余的空行
        pretty_xml = '\n'.join([line for line in pretty_xml.split('\n') if line.strip()])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        print(f"GPX文件已成功生成: {output_file}")
        return True
        
    except Exception as e:
        print(f"写入GPX文件时发生错误: {e}")
        return False

def main():
    # 固定的输入文件路径
    input_file = "backUpData/backUpData.csv"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 找不到文件 {input_file}")
        print("请确保文件位于 backUpData 文件夹中")
        input("按任意键退出...")
        return
    
    # 生成输出文件路径（同一目录，相同文件名，不同扩展名）
    output_file = "backUpData/backUpData.gpx"
    
    print(f"正在转换文件: {input_file}")
    print(f"输出文件: {output_file}")
    print("-" * 50)
    
    success = create_gpx_from_csv(input_file, output_file)
    
    if success:
        print("-" * 50)
        print("✅ 转换完成！")
        print(f"GPX文件已保存到: {output_file}")
    else:
        print("-" * 50)
        print("❌ 转换失败！")
    
    print("-" * 50)
    input("按任意键退出...")

if __name__ == "__main__":
    main()