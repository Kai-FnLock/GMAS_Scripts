import argparse
import zipfile
import os
import glob
import re
from lxml import etree
import xmlschema
import logging
import shutil
from datetime import datetime, timedelta


# 验证KMZ文件是否符合KML的XSD模式
def validateKMZ(kml_content, defaultSchema = "schema22"):

    schema_file_path_22 = r'D:\MacBook\MacBookDocument\VSCode\SourceCode\KML-lib\kml_xsd\2.2.0\ogckml22.xsd'
    schema_file_path_23 = r'D:\MacBook\MacBookDocument\VSCode\SourceCode\KML-lib\kml_xsd\2.3.0\ogckml23.xsd'

    if defaultSchema == "schema22":
        schema = xmlschema.XMLSchema(schema_file_path_22)
    elif defaultSchema == "schema23":
        schema = xmlschema.XMLSchema(schema_file_path_23)
    else:
        return print("无效的输入参数")
    
    try:
        schema.validate(kml_content)
        logging.info("XML文件与XSD验证通过")
    except xmlschema.validators.exceptions.XMLSchemaValidationError as e:
        logging.error("XML文件与XSD验证不符")
        # logging.error(f"{kml_content}XML文件与XSD验证不符")
        # logging.error(f"XML文件与XSD验证不符: {e}")
    return None

def extract_point_data_from_description(description_content):
    obspid_pattern = re.compile(r'<td>(\d{5}[A-Za-z]\d{3})</td>')
    longitude_pattern = re.compile(r'<td>Longitude</td>\s*<td>(-?\d+\.\d+)</td>')
    latitude_pattern = re.compile(r'<td>Latitude</td>\s*<td>(-?\d+\.\d+)</td>')

    obspid_match = obspid_pattern.search(description_content)
    longitude_match = longitude_pattern.search(description_content)
    latitude_match = latitude_pattern.search(description_content)

    obspid = obspid_match.group(1) if obspid_match else None
    longitude = float(longitude_match.group(1)) if longitude_match else None
    latitude = float(latitude_match.group(1)) if latitude_match else None

    return obspid, longitude, latitude


def merge_and_render_KMZ(input_folder, output_kmz_file):

    icon_file = r'D:\RouteDesigen\Layer0_Symbol_Square.png'

# 创建临时目录
    temp_dir = os.path.join(input_folder, "temp_kmz")
    os.makedirs(temp_dir, exist_ok=True)
    files_dir = os.path.join(temp_dir, 'files')
    os.makedirs(files_dir, exist_ok=True)

# 创建临时KML文件
    temp_kml_file = os.path.join(input_folder, "temp_combined.kml")

    linestringCoords_list = []
# 遍历文件夹中的所有KMZ文件，提取线要素
    for kmz_file in glob.glob(os.path.join(input_folder, '*.kmz')):
        logging.info(f"准备验证KMZ文件(线要素): {kmz_file}")
        with zipfile.ZipFile(kmz_file, 'r') as kmz:
            for file_name in kmz.namelist():
                if file_name.endswith('.kml'):
                    with kmz.open(file_name) as kml_file:
                        kml_content = kml_file.read()
                        validateKMZ(kml_content)
                        root = etree.fromstring(kml_content, parser=etree.XMLParser(encoding='utf-8',recover=True))
                    # 查找所有的Placemark元素下的LineString元素
                        for placemark in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
                            linestring = placemark.find('.//{http://www.opengis.net/kml/2.2}LineString')
                            if linestring is not None:
                                coordinates = linestring.find('.//{http://www.opengis.net/kml/2.2}coordinates')
                                if coordinates is not None:
                                    linestringCoords_list.append(coordinates.text.strip())
    logging.info(f"总线要素数量: {len(linestringCoords_list)}")

    points_dict = {}
    # 遍历文件夹中的所有KMZ文件，提取点要素
    for kmz_file in glob.glob(os.path.join(input_folder, '*.kmz')):
        # initial_point_count = len(points_dict)  # 记录处理前的点要素数量    
        with zipfile.ZipFile(kmz_file, 'r') as kmz:
            for file_name in kmz.namelist():
                if file_name.endswith('.kml'):
                    with kmz.open(file_name) as kml_file:
                        kml_content = kml_file.read()
                        root = etree.fromstring(kml_content, parser=etree.XMLParser(encoding='utf-8',recover=True))
                    # 通过Point元素提取点要素，Point元素下的name元素为OBSID，coordinates元素为经纬度
                        countNum = 0
                        for placemark in root.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
                            point = placemark.find('.//{http://www.opengis.net/kml/2.2}Point')
                            if point is not None:
                                name = placemark.find('.//{http://www.opengis.net/kml/2.2}name')
                            # logging.info(f'{len(name)}')
                                if name is not None and name.text:
                                # logging.info(f"{name.text}")
                                    obspid_pattern = re.compile(r'\d{5}[A-Za-z]\d{3}')
                                    if obspid_pattern.match(name.text):
                                        obspid = name.text
                                        longitude = point.find('.//{http://www.opengis.net/kml/2.2}coordinates').text.split(',')[0]
                                        latitude = point.find('.//{http://www.opengis.net/kml/2.2}coordinates').text.split(',')[1]
                                        points_dict[obspid] = {
                                        'longitude': longitude,
                                        'latitude': latitude
                                    }
                                        countNum += 1
                                    else:
                                        logging.info(f"KMZ文件 {kmz_file} 中的点要素{obspid}格式不正确")
                    # logging.info(f"KMZ文件 {kmz_file} 中的点要素数量(Placemark统计): {countNum}")
                                    # logging.info(f"KMZ文件 {kmz_file} 中的点: {name.text}")
                    # 通过description元素提取点要素，description元素中包含OBSID、经度和纬度
                    # 通过description元素提取点要素，
                        countNum = 0
                        for description in root.findall('.//{http://www.opengis.net/kml/2.2}description'):
                            if description is not None and description.text:
                                obspid, longitude, latitude = extract_point_data_from_description(description.text)
                            # if obspid == None or longitude == None or latitude == None:
                            #     logging.info(f"KMZ文件 {kmz_file} 中的点要素没有OBSID{obspid}或经度{longitude}或纬度{latitude}")
                                if obspid and longitude and latitude:
                                    if not obspid in points_dict:
                                        points_dict[obspid] = {
                                        'longitude': longitude,
                                        'latitude': latitude
                                    }
                                        countNum += 1
                            # 如果OBSID、经度和纬度中有一个为空，则记录日志
                                if obspid and not longitude and not latitude:
                                    logging.info(f"KMZ文件 {kmz_file} 中的点要素{obspid}没有经度或纬度")
                        if countNum > 0:
                            logging.info(f"KMZ文件 {kmz_file} 通过Description的点要素数量增加: {countNum}")
                        countNum = 0
                        for obspid, coords in points_dict.items():
                            if coords['longitude'] == None or coords['latitude'] == None:
                                logging.info(f"KMZ文件 {kmz_file} 中的点要素{obspid}没有经度或纬度")
                                countNum += 1
                    # if countNum > 0:
                    #     logging.info(f"KMZ文件 {kmz_file} 中无坐标的点有{countNum}个")

        # added_points = len(points_dict) - initial_point_count  # 计算增加的点要素数量
        # logging.info(f"KMZ文件 {kmz_file} 增加的点要素数量: {added_points}")

    logging.info(f"总点要素数量: {len(points_dict)}")


    # ----------------------------封装KMZ文件--------------------------------
    document = etree.Element("Document")

    # 添加线样式
    style = etree.SubElement(document, "Style", id="lineStyle")
    line_style = etree.SubElement(style, "LineStyle")
    color = etree.SubElement(line_style, "color")
    color.text = "ff000000"  # 黑色，格式为 AABBGGRR
    width = etree.SubElement(line_style, "width")
    width.text = "1"  # 线宽度

    # 添加线数据
    for i, coordinates in enumerate(linestringCoords_list):
        placemark = etree.SubElement(document, "Placemark")
        style_url = etree.SubElement(placemark, "styleUrl")
        style_url.text = "#lineStyle"
        name = etree.SubElement(placemark, "name")
        name.text = f"Route {i+1}"
        linestring = etree.SubElement(placemark, "LineString")
        coord_elem = etree.SubElement(linestring, "coordinates")
        coord_elem.text = coordinates

    # 添加点样式
    style = etree.SubElement(document, "Style", id="pointStyle")
    icon_style = etree.SubElement(style, "IconStyle")
    icon = etree.SubElement(icon_style, "Icon")
    href = etree.SubElement(icon, "href")
    href.text = "files/Layer0_Symbol_Square.png"  # 使用自定义图标的 URL

    # 添加点要素
    for obspid, coords in points_dict.items():
        placemark = etree.SubElement(document, "Placemark")
        style_url = etree.SubElement(placemark, "styleUrl")
        style_url.text = "#pointStyle"
        name = etree.SubElement(placemark, "name")
        name.text = obspid
        point = etree.SubElement(placemark, "Point")
        coordinates = etree.SubElement(point, "coordinates")
        coordinates.text = f"{coords['longitude']},{coords['latitude']}"

    # 保存KML文件
    tree = etree.ElementTree(document)
    tree.write(temp_kml_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")

    # 将PNG文件移动到files文件夹中
    shutil.copy(icon_file, files_dir)

    # 压缩为KMZ文件
    with zipfile.ZipFile(output_kmz_file, 'w', zipfile.ZIP_DEFLATED) as kmz:
    # 将doc.kml文件添加到KMZ文件中
        kmz.write(temp_kml_file, 'doc.kml')
    # 将files文件夹中的PNG文件添加到KMZ文件中
        for root, _, files in os.walk(files_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                kmz.write(file_path, arcname)

    # 删除临时目录
    shutil.rmtree(temp_dir)
    # 删除临时KML文件
    os.remove(temp_kml_file)

    logging.info(f"KMZ文件已保存到: {output_kmz_file}")

    return len(points_dict)


def parse_args():
    # 无参数输入时，默认date_str为当天，有参数时，为指定参数
    parser = argparse.ArgumentParser(description="处理日期字符串")
    parser.add_argument("date_str", nargs='?', default=datetime.now().strftime("%Y%m%d"), type=str, help="日期字符串，格式为 YYYYMMDD")
    return parser.parse_args()

def main():
    args = parse_args()
    date_str = args.date_str
    workspace = r"D:\RouteDesigen"

    # 将日期字符串转换为datetime对象
    date = datetime.strptime(date_str, "%Y%m%d")
    # 格式化日期字符串，例如：年月日2021010
    yearAndmonth_str = date.strftime("%Y%m")

    # 定义输入和输出路径
    input_folder = os.path.join(workspace, yearAndmonth_str, date_str, "Finished points")
    output_kmz_file = os.path.join(workspace, yearAndmonth_str, date_str, f"GMAS_Points_and_tracks_until_{date_str}.kmz")

    # 设置日志记录文件位置
    # log_file = r'D:\RouteDesigen\202410\20241023\validateKMZfiles.log'
    log_file = os.path.join(workspace, yearAndmonth_str, date_str, f"validateKMZfiles{date_str}.log")
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # 创建文件处理器
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # # 创建控制台处理器
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # 获取根日志记录器并添加处理器
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)
    # logger.propagate = False        # 防止日志消息被传递到根日志记录器

    merge_and_render_KMZ(input_folder, output_kmz_file)
    
    # 关闭处理器
    file_handler.close()
    # console_handler.close()
    # 移除处理器
    logger.removeHandler(file_handler)
    # logger.removeHandler(console_handler)
    # 关闭日志记录器
    logging.shutdown()
    print("日志记录器关闭")

if __name__ == "__main__":
    main()