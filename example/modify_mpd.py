import os
import csv
import xml.etree.ElementTree as ET
from collections import defaultdict

def get_files(path):
    d = defaultdict(list)
    for f in os.listdir(path):
        full_name = os.path.join(path, f)
        if os.path.isfile(full_name) and f.split('.')[-1] == 'm4s':
             size = os.path.getsize(full_name)
             size = (size)/1024 #KB
             resolution = f.split('_')[1]
             number = int(f.split('_')[2].split('.')[0])
             scale = "KB"
             (f, size)
             print(f, size, scale, number)
             d[resolution].append((f, size, scale, number))
    return d

def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def parseXML(xmlfile, files):
    ET.register_namespace("", "urn:mpeg:dash:schema:mpd:2011")
    tree = ET.parse(xmlfile)
    root = tree.getroot()

    SegmentTemplate = root.find('{urn:mpeg:dash:schema:mpd:2011}SegmentTemplate')
    s = None
    if SegmentTemplate is not None:
       s = [s for s in SegmentTemplate.iter[0] ]

    for child in root.iter():
        if child.tag == '{urn:mpeg:dash:schema:mpd:2011}AdaptationSet':
           child.set("mimeType", "video/mp4")
           if s is not None:
              child.remove(s)

    for child in root.iter('{urn:mpeg:dash:schema:mpd:2011}Representation'):
        if s is not None:
             SegmentTemplate = child.append(s)
        id = child.attrib['id']
        f_sort = sorted(files[id], key=lambda x: x[3])
        for f in f_sort:
            s_size = ET.SubElement(child, 'SegmentSize')
            s_size.set('id', f[0])
            s_size.set('size', str(f[1]))
            s_size.set('scale', f[2])

    indent(root)

    with open('output_dash2.mpd', 'wb') as f:
        ET.ElementTree(root).write(f,  encoding='utf-8', xml_declaration=True)

def main():
    files = get_files('.')
    newsitems = parseXML('output_dash.mpd', files)

if __name__ == "__main__":
    main()
