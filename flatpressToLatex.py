from pylatex import Document, Section, Subsection, Tabular, Math, TikZ, Axis, Plot, Figure, Matrix, Alignat, Command, NoEscape
from pylatex.utils import italic
import shutil
import datetime
import sys
import traceback
import time
import argparse
import os
import re

class Flatpress2Latex():
    newpath = r'images' 

    def __init__(self, args):
        self.imgPaths = args.images
        self.fromDate = args.fromDate
        self.toDate = args.toDate
        self.contentRootPath = args.content
        self.outputTexfile = args.output
        self.entries = {}

    def getImagesFromEntry(self, entryText):
        ''' Finds image file name within text entry.'''
        result = []
        patternJpg = r'\w+\.jpg'
        patternJpeg = r'\w+\-\w+\.jpeg'
        resultJpg = re.findall(patternJpg, entryText)
        resultJpeg = re.findall(patternJpeg, entryText)
        result = result + resultJpg + resultJpeg
        return result

    def cleanImgPatternFromText(self, entryText):
        '''Removes from text [img] tags'''
        pattern = r'(\[img=)[^]]*(\])'
        result = re.sub(pattern,'',entryText)
        return result or entryText

    def removeItalicSymbols(self, entryText):
        '''Clean italic markdown symbols'''
        cleanedText = entryText.replace('[i]',r'\emph{').replace(r'[/i]','}')
        return cleanedText

    def cleanText(self, entryText):
        '''Remove markdown patterns.'''
        text = self.cleanImgPatternFromText(entryText)
        text = self.removeItalicSymbols(text)
        return text

    def parseEntry(self, entry):
        '''Parse entry as a dict.'''
        pieces = entry.split('|')
        if len(pieces) == 11:
            timestamp = pieces[9]
            text = pieces[5]
            images = self.getImagesFromEntry(text)
            entryDict = {
                "title" : pieces[3],
                "text" : self.cleanText(text),
                "images" : images,
                "author" : pieces[7]
            }
            return timestamp, entryDict
        else:
            return False,''

    def filterEntries(self):
        '''Filter entries by date'''
        fromTimestamp = time.mktime(time.strptime(self.fromDate, '%Y-%m-%d'))
        toTimestamp = time.mktime(time.strptime(self.toDate, '%Y-%m-%d'))
        keys2pop =  []
        for key,value in self.entries.items():
            if not int(fromTimestamp) < int(key) < int(toTimestamp):
                keys2pop.append(key)
        for key in keys2pop:
            _ = self.entries.pop(key)

    def gatherEntries(self):
        '''Retrieves all entries.'''
        for root,firs, files in os.walk(self.contentRootPath):
            path = root.split(os.sep)
            print((len(path) - 1) * '-', os.path.basename(root))
            for file in files:
                try:
                    filepath = os.path.join(root,file)
                    if file.endswith('.txt'):
                        with open(filepath) as f:
                            entry = f.read()
                            timestamp, entryDict = self.parseEntry(entry)
                            if timestamp:
                                self.entries[timestamp] = entryDict
                        print(len(path) * '-', file)
                except Exception as e:
                    print('FILE: %s\nPATH: %s' % (file, path))
                    print('ERROR: %s\n-----' %str(e)+str(traceback.format_exc()))

    def saveImages(self, imageList):
        '''Copy images to a local folder within execution path'''
        newList = []
        breakLoop = False
        if imageList:
            if not os.path.exists(self.newpath):
                os.makedirs(self.newpath)
            for image in imageList:
                print('[INFO] - \tImage:%s'%image)
                for path in self.imgPaths:
                    for root, dirs, files in os.walk(path):
                        if image in files:
                            shutil.copyfile(
                                os.path.join(root, image), 
                                os.path.join(self.newpath, image)
                            )
                            newList.append(os.path.join(self.newpath, image))
                            breakLoop = True
                            break
                    if breakLoop:
                        break
        return newList

    def buildDocument(self):
        '''Builds the latex document adding entries in chronological order.'''
        geometry_options = {"tmargin": "2cm", "lmargin": "2cm", "rmargin":"2cm"}
        doc = Document(geometry_options=geometry_options)
        doc.preamble.append(Command('usepackage',arguments='wrapfig'))
        doc.preamble.append(Command('usepackage',arguments='graphicx'))
        doc.preamble.append(Command('usepackage',arguments='sectsty'))
        doc.preamble.append(Command('sectionfont',arguments=NoEscape(r'\fontsize{24}{15}\selectfont')))
        keys = list(self.entries.keys())
        keys.sort()
        for key in keys:
            entry = self.entries[key]
            print('[INFO] - Processing %s' % entry['title'])
            imageList = self.saveImages(entry['images'])
            doc.append(Command('newpage'))
            with doc.create(Section(entry['title'],numbering=False)):
                doc.append(datetime.datetime.fromtimestamp(int(key)))
                doc.append(Command('newline'))
                if imageList:
                    doc.append(Command('begin',arguments=['wrapfigure','o',NoEscape(r'0.5\textwidth')]))
                    for image in imageList:
                        doc.append(Command('includegraphics',options=NoEscape(r'width=0.5\textwidth'),arguments=NoEscape(image)))
                        #headerImage.add_caption('Caption example')
                    doc.append(Command('vspace',arguments=NoEscape('-110pt')))
                    doc.append(Command('end',arguments='wrapfigure'))
                else:
                    doc.append(Command('newline'))
                doc.append(NoEscape(entry['text'].strip()))

        doc.generate_tex(self.outputTexfile)

    def run(self):
        '''Main method.'''
        print('Start')
        self.gatherEntries()
        self.filterEntries()
        self.buildDocument()
        print('End')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(
        description='''Converts Flatpress' blog entries into a latex document.''',
        epilog="""Example: python flatpressToLatex.py -fromDate 2023-01-01 -toDate 2023-03-31 -images /home/user/image1 /home/user/image2 -content /var/www/html/blog/fp-content/content""")
    parser.add_argument("-fromDate", type=str, help="Include entries with this date as start: format YYYY-MM-DD.")
    parser.add_argument("-toDate", type=str, help="Include entries with this date as end: format YYYY-MM-DD.")
    parser.add_argument("-images", type=str, nargs='*', help="Paths of image folders")
    parser.add_argument("-content", type=str, help="Root folder (fp-content/content)")
    parser.add_argument("-output", type=str, help="Name of the tex file to generate (without tex extension)")
    args = parser.parse_args()
    f2l = Flatpress2Latex(args)
    f2l.run()