import os

#Python code to illustrate parsing of XML files 
# importing the required modules 
import csv 
import xml.etree.ElementTree as ET 

# Modificar o SegmentTemplate duration
# timescale*tempo_de_cada_segmento = duration
# https://community.akamai.com/customers/s/article/How-to-determine-number-of-segments-for-DASH-stream?language=en_US

def get_files(path):

    
    d = {'240p': [], '360p': [], '480p': [], '720p':[], '7202p': [], '1080p': [], '10802p': [], '1440p': [], '14402p': [], '2560p': [], '25602p': []}
    for f in os.listdir(path):
        full_name = os.path.join(path, f)

        if os.path.isfile(full_name) and f.split('.')[-1] == 'm4s':

             size = os.path.getsize(full_name)
             size = (size)/1024 #KB
             resolution = f.split('_')[1]
             number = int(f.split('_')[2].split('.')[0])
             scale = "KB"
             (f, size)
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

    # create element tree object 
    tree = ET.parse(xmlfile) 
  
    # get root element 
    root = tree.getroot() 

    s = [s for s in root.iter('{urn:mpeg:dash:schema:mpd:2011}SegmentTemplate')][0]

    for child in root.iter():
        if child.tag == '{urn:mpeg:dash:schema:mpd:2011}AdaptationSet': 
            child.set("mimeType", "video/mp4")
            child.remove(s)
  
    for child in root.iter('{urn:mpeg:dash:schema:mpd:2011}Representation'):
        SegmentTemplate = child.append(s)
        id = child.attrib['id']
        f_sort = sorted(files[id], key=lambda x: x[3])
        for f in f_sort:
            
            s_size = ET.SubElement(child, 'SegmentSize')
            s_size.set('id', f[0])
            s_size.set('size', str(f[1]))
            s_size.set('scale', f[2])
    
    indent(root)

    with open('person.xml', 'wb') as f:
        ET.ElementTree(root).write(f,  encoding='utf-8', xml_declaration=True)
     
def main(): 
  
    # parse xml file 
    files = get_files('.')
    newsitems = parseXML('output_dash.mpd', files) 
      
      
if __name__ == "__main__": 
  
    # calling main function 
    main()     
