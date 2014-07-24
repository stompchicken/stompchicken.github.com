#!/usr/bin/python
import argparse
import codecs
import os
import os.path
import logging
import shutil
import sys
import time
import logging
import glob
import datetime
import dateutil.parser
import shutil

import watchdog
from watchdog.observers import Observer
import jinja2
import markdown

"""

Article meta

title - the html head/title
template - the jinja template used

"""


def copy_file(source_dir, target_dir, rel_path):
    source_path = os.path.join(source_dir, rel_path)
    target_path = os.path.join(target_dir, rel_path)
    if not os.path.exists(os.path.dirname(target_path)):
        os.makedirs(os.path.dirname(target_path))
    shutil.copyfile(source_path, target_path)
    logging.info('Copy:\t%s' % rel_path)

def convertMarkdown(source_dir, target_dir, relpath, base_url, indexer):

    source_path = os.path.join(source_dir, relpath)
    basename, extension = os.path.splitext(relpath)
    target_path = os.path.join(target_dir, basename + ".html")

    logging.info('Convert:\t%s' % relpath)

    # Convert markdown
    md = markdown.Markdown(extensions=['meta', 'fenced_code', 'codehilite', 'footnotes', 'tables'])
    with codecs.open(source_path, "r", encoding="utf-8") as input_file:
        body = md.convert(input_file.read())

    # Get page title from metadata
    if 'title' not in md.Meta:
        logging.error("No title field in metadata")
        return
    title = md.Meta['title'][0]

    # Get category
    if 'category' not in md.Meta:
        logging.warning("No category field in metadata")
        category = "Other stuff"
    else:
        category = md.Meta['category'][0]

    # Get last modified date
    timestamp = time.gmtime(os.path.getmtime(source_path))
    last_modified = time.strftime("%a, %d %b %Y", timestamp)

    # Load template
    template_name = "default.jinja"
    if 'template' in md.Meta:
        template_name = md.Meta['template'][0]
    template = jinja_env.get_template(template_name)
    html = template.render({"body": body, "base_url": base_url, "title": title})

    # Save the generated HTML
    if not os.path.exists(os.path.dirname(target_path)):
        os.makedirs(os.path.dirname(target_path))

    with codecs.open(target_path, "w+", encoding="utf-8") as output_file:
        output_file.write(html)

    if indexer:
        indexer.add_document({"title": title, "category": category, "last_edited": last_modified})

def publish(path, source_dir, target_dir, base_url, indexer):
    # Path of file relative to the source directory
    rel_path = os.path.relpath(path, source_dir)
    directory, filename = os.path.split(path)
    basename, extension = os.path.splitext(filename)
    if extension == ".md":
        convertMarkdown(source_dir, target_dir, rel_path, base_url, indexer)
    elif extension in ['.css', '.png', '.jpg']:
        copy_file(source_dir, target_dir, rel_path)

class Indexer(object):
    def __init__(self):
        self.docs = []

    def add_document(self, doc):
        self.docs.append(doc)

    def generate(self, target_dir, base_url):
        logging.info("Index:\t%d documents" % len(self.docs))
        # Load template
        template_name = "index.jinja"
        template = jinja_env.get_template(template_name)

        print self.docs
        html = template.render({"docs": self.docs, "base_url": base_url})

        # Save the generated HTML
        target_path = os.path.join(target_dir, "index.html")
        with codecs.open(target_path, "w+", encoding="utf-8") as output_file:
            output_file.write(html)

class FileEventHandler(watchdog.events.FileSystemEventHandler):
    """Publish HTML in response to updates to the file system"""
    def __init__(self, source_dir, target_dir, base_url):
        self.source_dir = source_dir
        self.target_dir = target_dir
        self.base_url = base_url

    def on_any_event(self, event):
        if event.is_directory:
            return
        else:
            publish(event.src_path, self.source_dir, self.target_dir, self.base_url, None)

if __name__ == '__main__':
    FORMAT = '[%(levelname)s]%(message)s'
    logging.basicConfig(level=logging.DEBUG, format=FORMAT)

    parser = argparse.ArgumentParser(description='Static site generator')
    parser.add_argument('source', type=unicode, help='Source directory')
    parser.add_argument('target', type=unicode, help='Destination directory')
    parser.add_argument('-b', '--base_url', type=unicode, help='Base url')
    parser.add_argument('-w', '--watchdog', help='Watchdog mode', action='store_true')
    args = parser.parse_args()

    base_dir = os.getcwd()
    source_dir = os.path.join(base_dir, args.source)
    target_dir = os.path.join(base_dir, args.target)
    base_url = args.base_url or os.path.join(base_dir, args.target)

    logging.debug("Source:"+source_dir)
    logging.debug("Target:"+target_dir)

    if os.path.exists(target_dir):
        logging.debug("Wiping out target directory")
        shutil.rmtree(target_dir)

    # Initialise jinja
    template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(args.source, "templates"))
    jinja_env = jinja2.Environment(loader=template_loader)

    # Do a complete publish of source directory
    indexer = Indexer()
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            publish(os.path.join(source_dir, root, filename), source_dir, target_dir, base_url, indexer)
    indexer.generate(target_dir, base_url)

    # Monitor file system and re-publish on filesystem changes
    if args.watchdog:
        logging.info("Entering watchdog mode...")
        observer = Observer()
        handler = FileEventHandler(source_dir, target_dir, base_url)
        observer.schedule(handler, path=base_dir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logging.debug("Caught CTRL-C")
            observer.stop()
            observer.join()

    logging.debug("Terminating")
