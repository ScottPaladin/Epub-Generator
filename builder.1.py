#!/usr/bin/env python3

from jinja2 import Template
from lxml import etree, objectify
import os, shutil, weakref
from argparse import Namespace
import epub
from nt import mkdir
import argparse
from time import sleep


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--recipe', help="XML file containing Book information", required=True)
parser.add_argument('--distributer', help="distributer", default='Backmatter')
args = parser.parse_args()

file = args.recipe
campaign = "Backmatter"
distributer = args.distributer

# lookup = {
#           'title': '',
#           'author': '',
#           'cover': '',
#           'slug': ''
#           }
#     
# copymanifest = [
#                 ('templates/style.css', 'style.css'),
#                 ('templates/page_styles.css', 'page_styles.css')
#                 ]
# 
# finalmanifest = []
# 
templatedict = {
                'cover': 'templates/titlepage.html',
                'frontmatter': 'templates/frontmatter.html',
                'toc': 'templates/tableofcontents.html',
                'story': 'templates/storypage.html',
                'backmatter': 'templates/backmatter.html',
                'links': 'templates/backmatterlinks.html'
                }

authorpagedict = {
                  'Randall Rogue': 'http://dapperratpublishing.com/category/story/randall-rogue-stories/',
                  'Samantha Squire': 'http://dapperratpublishing.com/category/story/samantha-squire-stories/',
                  'Parker Paige': 'http://dapperratpublishing.com/category/story/parker-paige-stories/',
                  }

class Book():
    def __init__(self, file):
        self.stories = []
        self.links = []
        self.pages = []
        self.parse_file(file)
        self.renders = []
    
    def parse_file(self, file):
            xml = readfile(file)
            root = objectify.fromstring(xml)
            for i in root.metadata.getchildren():
                self.__dict__[i.tag] = str(i)
            for i in root.content.getchildren():
                i = str(i)
                if i.endswith(".xml"):
                    self.add_story(None, None, i)
                elif i.endswith(".html"):
                    self.add_story(root.metadata.title, i, None)
            for i in root.backmatter.getchildren():
                self.add_link(str(i))
            for story in self.stories:
                story.parse_pointer()
            for link in self.links:
                link.parse_pointer()
            for n, story in enumerate(self.stories):
                story.ident = "story" + str(n)
            coverfile = 'cover.jpg'
#             copymanifest.append((self.cover, coverfile))
#             finalmanifest.append(coverfile)
                            

    def add_story(self, title, content, pointer):
        self.stories.append(Story(title, content, pointer))
            
    def add_link(self, pointer):
        self.links.append(Booklink(pointer))
    
    def add_page(self, index, pagetype, pagename, tocref, refobject=None):
        self.pages.append(Page(self, index, pagetype, pagename, tocref, refobject))

class Story():     
    def __init__(self, title=None, content=None, pointer=None, ident=None):
        self.title = title
        self.content = content
        self.pointer = pointer
        self.ident = ident
    
    def parse_pointer(self):
        if self.content is None and self.pointer is not None:
            xml = readfile(self.pointer)
            root = objectify.fromstring(xml)
            self.title = str(root.metadata.title)
            self.content = str(root.content.story)
        elif self.content is not None:
            print("Story already has content")
        elif self.pointer is None:
            print("Story does not have pointer")

class Booklink():
    def __init__(self, pointer=None):
        self.pointer = pointer
    
    def parse_pointer(self):
        if self.pointer is not None:
            xml = readfile(self.pointer)
            root = objectify.fromstring(xml)
            for i in root.metadata.getchildren():
                self.__dict__[i.tag] = str(i)
            self.pointer = None
        elif self.pointer is None:
            print("Link does not have pointer")

class Page():
    def __init__(self, parent, index, pagetype, pagename, tocref, refobject):
        self.index = index
        self.pagetype = pagetype
        self.pagename = pagename
        self.tocref = tocref
        self.refobject = refobject
        self.parent = weakref.proxy(parent)

def readfile(file):
    # simple with open command, returns contents of file
    with open(file, encoding="utf8")as f:
        return(f.read())

def writefile(file, data):
    # simple writefile command, puts data in file, returns nothing
    with open(file, 'wb') as f:
        f.write(bytes(data, 'UTF-8'))

def checkcopy(files, dest):
    # copies a list of files to destination
    for line in files:
        (src, dstname) = line
        shutil.copyfile(src, dest + dstname)
        finalmanifest.append(dstname)
        
def build_pages(book):
    counter = 0
#     book.add_page(counter, 'cover', 'cover.html')
#     counter += 1
#     book.add_page(counter, 'frontmatter', book.slug + str(counter).zfill(3) + ".html")
#     counter += 1 
#     book.add_page(counter, 'toc', book.slug + str(counter).zfill(3) + ".html")
#     counter += 1 
    for story in book.stories:
        pagetitle = book.slug + str(counter).zfill(3) + ".html"
        book.add_page(counter, 'story', pagetitle, story.title, story)
        story.pagetitle = pagetitle
        counter += 1
    book.add_page(counter, 'backmatter', book.slug + str(counter).zfill(3) + ".html", 'More by this Author', book.links)
    book.authorpage = authorpagedict.get(book.author)
    book.bundlepage = book.slug + str(counter).zfill(3) + ".html"

def render_page(page):
    template = templatedict.get(page.pagetype)
    template = readfile(template)
    if page.pagetype is 'story':
        content = readfile(page.refobject.content)
        storytitle = page.refobject.title
        ident = str(page.refobject.ident)
    elif page.pagetype is 'backmatter':
        make_bundle_links(page.refobject, page.parent)
        content = page.refobject
        storytitle = None
        ident = page.pagetype
    elif page.pagetype is 'toc':
        content = make_toc(page.parent)
        storytitle = None
        ident = page.pagetype
    else:
        content = None
        storytitle = None
        ident = page.pagetype
    authorlink = make_target_url(page.parent.authorpage, page.parent)
    pagerender = Template(template).render(
                                    author=page.parent.author,
                                    title=page.parent.title,
                                    content=content,
                                    storytitle=storytitle,
                                    ident=ident,
                                    authorlink=authorlink,
                                    )
#     finalmanifest.append(page.pagename)
    page.render = pagerender
    

def make_bundle_links(links, book):
    for link in links:
        newpath = flatten_link(link.thumb)
#         copymanifest.append((link.thumb, newpath))
        link.newpath = newpath
        link.targeturl = make_target_url(link.storeurl, book)

def flatten_link(link):
    (a, b) = link.split('/')
    return(b)

def make_target_url(storeurl, book):
    return(storeurl + "?&amp;utm_source=" + book.slug + "&amp;utm_medium=" + campaign + "&amp;utm_campaign=" + distributer)

def make_toc(book):
    results = []
    for page in book.pages:
        if type(page.refobject) is Story:
            a = page.refobject.ident
            b = page.refobject.title
            c = page.refobject.pagetitle
            results.append((a, b, c))
    results.append(('backmatter', 'More by this Author', book.bundlepage))
    return(results)


def make_epub_from_book(book):
    epubf = epub.EpubBook()
    epubf.setTitle(book.title)
    epubf.addCreator(book.author)
    epubf.addCover(book.cover)
    epubf.addMeta("publisher", book.publisher)
    epubf.addTitlePage()
    epubf.addTocPage()
    epubf.addCss('templates/style.css', 'style.css')
    epubf.addCss('templates/page_styles.css', 'page_styles.css')
    for page in book.pages:
        n1 = epubf.addHtml('', page.pagename, page.render)
        epubf.addSpineItem(n1)
        epubf.addTocMapNode(n1.destPath, page.tocref)
    for link in book.links:
        epubf.addImage(link.thumb, link.newpath)
    rootDir = book.slug + '-ep/'
    epubf.createBook(rootDir)
    epubf.createArchive(rootDir, book.slug +'.epub')
    epubf.checkEpub('epubcheck/epubcheck.jar', book.slug +'.epub')
    sleep(3)
    shutil.rmtree(rootDir)
     
  
    
workbook = Book(file)

print(workbook.author)
print(workbook.stories)
for story in workbook.stories:
    print(story.title, story.content, story.pointer)
for link in workbook.links:
    print(link.title, link.storeurl)
build_pages(workbook)
for page in workbook.pages:
    render_page(page)
#checkcopy(copymanifest, workbook.slug + "/")

#make_ncx(workbook)
#make_content_opf(workbook, finalmanifest)



    
make_epub_from_book(workbook)