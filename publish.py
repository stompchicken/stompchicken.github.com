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
import http.server
import socketserver

import watchdog
from watchdog.observers import Observer
import jinja2
import markdown

"""

Article meta

title - the html head/title
template - the jinja template used
category - what to group it under
"""

site_name = "Loss and regret"

class Publisher(object):

    def __init__(self, source_root, target_root, base_url):
        self.source_root = source_root
        self.target_root = target_root
        self.base_url = base_url

        # Clear out target directory
        if os.path.exists(self.target_root):
            logging.debug("Wiping out target directory")
            shutil.rmtree(target_root)
        os.makedirs(target_root)

        # Initialise jinja
        template_loader = jinja2.FileSystemLoader(searchpath=os.path.join(self.source_root, "templates"))
        self.jinja_env = jinja2.Environment(loader=template_loader)

    def publish_all(self):
        # Do a complete publish of source directory
        indexer = Indexer()
        for root, dirs, files in os.walk(self.source_root):
            for filename in files:
                path = os.path.relpath(root, self.source_root)
                self.publish_file(os.path.join(path, filename), indexer)

        # Generate an index page
        indexer.generate(self.jinja_env, self.target_root, self.base_url)

    def publish_file(self, path, indexer):
        directory, filename = os.path.split(path)
        basename, extension = os.path.splitext(filename)
        if basename.startswith("."):
            pass
        elif extension == ".md":
            self.convert_markdown(path, indexer)
        elif extension in ['.css', '.png', '.jpg', '.js', '.ico']:
            self.copy_file(path)

    def copy_file(self, path):
        """Copies file from source to target"""
        logging.info('Copy:\t%s' % path)
        source_path = os.path.join(self.source_root, path)
        target_path = os.path.join(self.target_root, path)
        if not os.path.exists(os.path.dirname(target_path)):
            os.makedirs(os.path.dirname(target_path))
        shutil.copyfile(source_path, target_path)

    def convert_markdown(self, path, indexer):
        """Converts a markdown document in the source directory to an HTML
        document in the target directory"""
        logging.info('Convert:\t%s' % path)

        source_path = os.path.join(self.source_root, path)
        basename, extension = os.path.splitext(path)
        target_path = os.path.join(self.target_root, basename + ".html")

        # Convert markdown
        md = markdown.Markdown(extensions=['meta', 'fenced_code', 'codehilite(guess_lang=False)', 'footnotes', 'tables'])
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
        last_modified = time.strftime("%d %b %Y", timestamp)

        # Get slug
        slug = basename + ".html"
        if slug.endswith("index.html"):
            slug = slug.replace("index.html", "")

        # Load template
        template_name = "article.jinja"
        if 'template' in md.Meta:
            template_name = md.Meta['template'][0]
        template = self.jinja_env.get_template(template_name)

        doc = {
            "site_name": site_name,
            "body": body,
            "base_url": base_url,
            "title": title,
            "category": category,
            "slug": slug,
            "last_modified": last_modified,
            # A crude check to speed up non-maths pages
            "use_MathJax": "$" in body
        }
        html = template.render(doc)

        # Save the generated HTML
        if not os.path.exists(os.path.dirname(target_path)):
            os.makedirs(os.path.dirname(target_path))

        with codecs.open(target_path, "w+", encoding="utf-8") as output_file:
            output_file.write(html)

        if indexer and category != "noindex":
            indexer.add_document(doc)

class Indexer(object):
    """Keeps a record of all published documents and compiles and index page"""
    def __init__(self):
        self.docs = []

    def add_document(self, doc):
        self.docs.append(doc)

    def generate(self, jinja_env, target_root, base_url):
        logging.info("Index:\t%d documents" % len(self.docs))

        # Load template
        template_name = "index.jinja"
        template = jinja_env.get_template(template_name)

        html = template.render({"docs": self.docs, "base_url": base_url, "site_name": site_name})

        # Save the generated HTML
        target_path = os.path.join(target_root, "index.html")
        with codecs.open(target_path, "w+", encoding="utf-8") as output_file:
            output_file.write(html)

class FileEventHandler(watchdog.events.FileSystemEventHandler):
    """Publish HTML in response to updates to the file system"""
    def __init__(self, publisher):
        self.publisher = publisher

    def on_any_event(self, event):
        if event.is_directory:
            return
        else:
            path = os.path.relpath(event.src_path, self.publisher.source_root)
            self.publisher.publish_file(path, None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Static site generator')
    parser.add_argument('source', type=str, help='Source directory')
    parser.add_argument('target', type=str, help='Destination directory')
    parser.add_argument('-b', '--base_url', type=str, help='Base url')
    parser.add_argument('-w', '--watchdog', help='Watchdog mode', action='store_true')
    parser.add_argument('-d', '--debug', help='Debug logging', action='store_true')
    args = parser.parse_args()

    # Set up logging
    FORMAT = '[%(levelname)s] %(message)s'
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format=FORMAT)

    base_dir = os.getcwd()
    source_dir = os.path.join(base_dir, args.source)
    target_dir = os.path.join(base_dir, args.target)
    base_url = args.base_url or ""

    logging.debug("Source:"+source_dir)
    logging.debug("Target:"+target_dir)

    # Do a complete publish of source directory
    publisher = Publisher(source_dir, target_dir, base_url)
    publisher.publish_all()

    # Monitor file system and re-publish on filesystem changes
    if args.watchdog:
        logging.info("Entering watchdog mode...")
        observer = Observer()
        handler = FileEventHandler(publisher)
        observer.schedule(handler, path=source_dir, recursive=True)
        observer.start()

    current_dir = os.getcwd()
    try:
        os.chdir(target_dir)
        port = 8000
        handler = http.server.SimpleHTTPRequestHandler
        # To handle 'Address already in use error'
        # http://stackoverflow.com/questions/10613977/
        class MyTCPServer(socketserver.TCPServer):
            allow_reuse_address = True
        httpd = MyTCPServer(("", port), handler)
        logging.info("Starting server at port: %d" % port)
        while True:
            httpd.handle_request()

    except KeyboardInterrupt:
        logging.debug("Caught CTRL-C")
        logging.info("Shutting down server at port: %d" % port)
        if args.watchdog:
            observer.stop()
            observer.join()

    logging.debug("Terminating")
    os.chdir(current_dir)
