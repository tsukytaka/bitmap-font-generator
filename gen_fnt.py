# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
gen_fnt (https://github.com/aillieo/bitmap-font-generator)
Fast and easy way to generate bitmap font with images
Created by Aillieo on 2017-09-06
With Python 3.5
"""

from functools import reduce
from PIL import Image
import os
import re
import unpack
import bitstring
import cv2
import numpy
import processImageUtilities

DATA_DIR_ROOT = '../BillParcelOCR/TrainHWJapanese/Data/ETLCDB/'

def format_str(func):
    def wrapper(*args, **kw):
        ret = func(*args, **kw)
        ret = re.sub(r'[\(\)\{\}]', "", ret)
        ret = re.sub(r'\'(?P<name>\w+)\': ', "\g<name>=", ret)
        ret = re.sub(r', (?P<name>\w+)=', " \g<name>=", ret)
        ret = ret.replace("'", '"')
        return ret

    return wrapper


class FntConfig:
    def __init__(self):
        self.info = {
            "face": "NA",
            "size": 16,
            "bold": 0,
            "italic": 0,
            "charset": "",
            "unicode": 1,
            "stretchH": 100,
            "smooth": 1,
            "aa": 1,
            "padding": (0, 0, 0, 0),
            "spacing": (0, 0),
        }

        self.common = {
            "lineHeight": 19,
            "base": 26,
            "scaleW": 1024,
            "scaleH": 1024,
            "pages": 1,
            "packed": 0
        }

        self.pages = {}

    @format_str
    def __str__(self):
        return 'info ' + str(self.info) + '\ncommon ' + str(self.common) + '\n'


class CharDef:
    def __init__(self, id, file):
        self.file = file
        self.param = {
            "id": id,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "xoffset": 0,
            "yoffset": 0,
            "xadvance": 0,
            "page": 0,
            "chnl": 15
        }
        img = Image.open(self.file)
        self.ini_with_texture_size(img.size)

    def __init__(self, id, img):
        self.param = {
            "id": id,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "xoffset": 0,
            "yoffset": 0,
            "xadvance": 0,
            "page": 0,
            "chnl": 15
        }
        self.img = img
        self.ini_with_texture_size(img.size)

    @format_str
    def __str__(self):
        return 'char ' + str(self.param)

    def ini_with_texture_size(self, size):
        padding = fnt_config.info["padding"]
        self.param["width"], self.param["height"] = size[0] + padding[1] + padding[3], size[1] + padding[0] + padding[2]
        self.param["xadvance"] = size[0]
        self.param["xoffset"] = - padding[1]
        self.param["yoffset"] = - padding[0]

    def set_texture_position(self, position):
        self.param["x"], self.param["y"] = position

    def set_page(self, page_id):
        self.param["page"] = page_id


class CharSet:
    def __init__(self):
        self.chars = []

    def __str__(self):
        ret = 'chars count=' + str(len(self.chars)) + '\n'
        ret += reduce(lambda char1, char2: str(char1) + str(char2) + "\n", self.chars, "")
        return ret

    def add_new_char(self, new_char):
        self.chars.append(new_char)

    def sort_for_texture(self):
        self.chars.sort(key=lambda char: char.param["width"], reverse=True)
        self.chars.sort(key=lambda char: char.param["height"], reverse=True)


class PageDef:
    def __init__(self, page_id, file):
        self.param = {
            "id": page_id,
            "file": file
        }

    @format_str
    def __str__(self):
        return 'page ' + str(self.param)


class TextureMerger:
    def __init__(self, fnt_name):
        self.charset = CharSet()
        self.pages = []
        self.current_page_id = 0
        self.page_name_base = fnt_name

    def get_images(self):
        files = os.listdir('.')
        for filename in files:
            print("filename: ", filename)
            name, ext = filename.split('.')
            if ext.lower() == 'png':
                if len(name) == 1:
                    new_char = CharDef(ord(name), filename)
                    self.charset.add_new_char(new_char)
                elif name[0:2] == '__' and name[2:].isdigit():
                    new_char = CharDef(int(name[2:]), filename)
                    self.charset.add_new_char(new_char)
        self.charset.sort_for_texture()

    
    def readAllCharByIndex_1C(self, dataFolder, index):
        listChar = []
        for fileIndex in range(13):
            dataFilePath = dataFolder + 'ETL1C_{:02d}'.format(fileIndex+1)
            f = bitstring.ConstBitStream(filename=dataFilePath)
            print("dataFile = ", dataFilePath)
            numberRecord = 11560
            numberSet = 1445
            numberCategories = 8
            if fileIndex > 5 and fileIndex < 11:
                numberRecord = 11288
                numberSet = 1411
            elif fileIndex == 11:
                numberRecord = 11287
                numberSet = 1411
            elif fileIndex == 12:
                numberRecord = 4233
                numberSet = 1411
                numberCategories = 3
            
            for i in range(numberCategories):
                print("file %d categoy %d" % (fileIndex, i))
                recordIndex = (index - 1) + i*numberSet
                print("record %d" % (recordIndex))
                etln_record = unpack.ETL167_Record()
                record = etln_record.read(f, recordIndex)
                char = etln_record.get_char()
                img = etln_record.get_image()

                cvImg = numpy.array(img) 
                binImg = processImageUtilities.convertBinImg(cvImg)
                # listChar.append({'id': char, 'image':Image.fromarray(binImg)})
                listChar.append(CharDef(ord(char), Image.fromarray(binImg)))
                print("is char %s" % (char))

        return listChar

    def get_images_from_etlcdb(self, index):
        dataFolderPath = DATA_DIR_ROOT + 'ETL1/'
        listCharImg = self.readAllCharByIndex_1C(dataFolderPath, index)
        listCharAppend = []
        for charimg in listCharImg:
            if charimg.param["id"] not in listCharAppend:
                self.charset.add_new_char(charimg)
                listCharAppend.append(charimg.param["id"])

        self.charset.sort_for_texture()

        

    def save_page(self, texture_to_save):
        current_page_id = len(self.pages)
        file_name = self.page_name_base
        file_name += '_'
        file_name += str(current_page_id)
        file_name += '.png'
        try:
            texture_to_save.save(file_name, 'PNG')
            self.pages.append(PageDef(current_page_id, file_name))
        except IOError:
            print("IOError: save file failed: " + file_name)

    def next_page(self, texture_to_save):
        if texture_to_save:
            self.save_page(texture_to_save)
        texture_w, texture_h = fnt_config.common["scaleW"], fnt_config.common["scaleH"]
        return Image.new('RGBA', (texture_w, texture_h), (0, 0, 0, 0))

    def gen_texture(self):
        self.get_images()
        texture = self.next_page(None)
        padding = fnt_config.info['padding']
        spacing = fnt_config.info['spacing']
        pos_x, pos_y, row_h = 0, 0, 0
        for char in self.charset.chars:
            img = Image.open(char.file)
            size_with_padding = (padding[1] + img.size[0] + padding[3], padding[0] + img.size[1] + padding[2])
            if row_h == 0:
                row_h = size_with_padding[1]
                if size_with_padding[0] > texture.size[0] or size_with_padding[1] > texture.size[1]:
                    raise ValueError('page has smaller size than a char')
            need_new_row = texture.size[0] - pos_x < size_with_padding[0]
            if need_new_row:
                need_new_page = texture.size[1] - pos_y < size_with_padding[1]
            else:
                need_new_page = False

            if need_new_page:
                texture = self.next_page(texture)
                pos_x, pos_y = 0, 0
                row_h = size_with_padding[1]
            elif need_new_row:
                pos_x = 0
                pos_y += row_h + spacing[1]
                row_h = size_with_padding[1]
            char.set_texture_position((pos_x, pos_y))
            texture.paste(img, (pos_x + padding[1], pos_y + padding[0]))
            pos_x += size_with_padding[0] + spacing[0]
            char.set_page(self.current_page_id)
        self.save_page(texture)

    def gen_texture_from_etlcdb(self):
        self.get_images_from_etlcdb(int(self.page_name_base))
        #update size texture

        texture = self.next_page(None)
        padding = fnt_config.info['padding']
        spacing = fnt_config.info['spacing']
        pos_x, pos_y, row_h = 0, 0, 0
        for char in self.charset.chars:
            img = char.img
            size_with_padding = (padding[1] + img.size[0] + padding[3], padding[0] + img.size[1] + padding[2])
            if row_h == 0:
                row_h = size_with_padding[1]
                if size_with_padding[0] > texture.size[0] or size_with_padding[1] > texture.size[1]:
                    raise ValueError('page has smaller size than a char')
            need_new_row = texture.size[0] - pos_x < size_with_padding[0]
            if need_new_row:
                need_new_page = texture.size[1] - pos_y < size_with_padding[1]
            else:
                need_new_page = False

            if need_new_page:
                texture = self.next_page(texture)
                pos_x, pos_y = 0, 0
                row_h = size_with_padding[1]
            elif need_new_row:
                pos_x = 0
                pos_y += row_h + spacing[1]
                row_h = size_with_padding[1]
            char.set_texture_position((pos_x, pos_y))
            texture.paste(img, (pos_x + padding[1], pos_y + padding[0]))
            pos_x += size_with_padding[0] + spacing[0]
            char.set_page(self.current_page_id)
        self.save_page(texture)

    def pages_to_str(self):
        return reduce(lambda page1, page2: str(page1) + str(page2) + "\n", self.pages, "")


class FntGenerator:
    def __init__(self, fnt_name):
        self.fnt_name = fnt_name
        self.textureMerger = TextureMerger(fnt_name)

    def gen_fnt(self):
        self.textureMerger.gen_texture()
        fnt_file_name = self.fnt_name + '.fnt'
        try:
            with open(fnt_file_name, 'w', encoding='utf8') as fnt:
                fnt.write(str(fnt_config))
                fnt.write(self.textureMerger.pages_to_str())
                fnt.write(str(self.textureMerger.charset))
            fnt.close()
        except IOError:
            print("IOError: save file failed: " + fnt_file_name)

    def gen_fnt_from_etlcdb(self):
        self.textureMerger.gen_texture_from_etlcdb()
        fnt_file_name = self.fnt_name + '.fnt'
        try:
            with open(fnt_file_name, 'w', encoding='utf8') as fnt:
                fnt.write(str(fnt_config))
                fnt.write(self.textureMerger.pages_to_str())
                fnt.write(str(self.textureMerger.charset))
            fnt.close()
        except IOError:
            print("IOError: save file failed: " + fnt_file_name)


if __name__ == '__main__':
    fnt_config = FntConfig()
    isFolderImage = False
    if isFolderImage:
        full_path = os.path.abspath('.')
        print("full_path: ", full_path)
        cur_path = full_path.split('/')[-1]
        fnt_generator = FntGenerator(cur_path)
        fnt_generator.gen_fnt()
    else:
        fnt_generator = FntGenerator("1")
        fnt_generator.gen_fnt_from_etlcdb()
