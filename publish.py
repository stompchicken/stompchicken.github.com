import argparse
import markdown
import codecs
import os
import logging
import jinja2
import shutil
import sys
import time
import logging
from watchdog.observers import Observer
import watchdog
import glob
import dateutil.parser

class IndexedDocument(object):
    """A document to be added to a auto-generated index page"""
    def __init__(self, path):
        self.path = path
        directory, self.filename = os.path.split(path)
        self.basename, self.extension = os.path.splitext(self.filename)
        with codecs.open(path, "r", encoding="utf-8") as f:
            md = markdown.Markdown(extensions=['meta'])
            doc = md.convert(f.read())
        if 'index' in md.Meta:
            self.valid = False
        else:
            self.title = md.Meta.get('title', ['Untitled'])[0]
            self.summary = md.Meta.get('title', ['What we cannot speak of must be passed over in silence'])[0]
            self.date = md.Meta.get('date', ['40,000AD'])[0]
            self.valid = True

class Document(object):
    """A markdown page"""
    def __init__(self, directory, filename):
        self.directory = directory
        self.filename = filename # filename with extension
        self.basename, self.extension = os.path.splitext(filename)
        self.path = os.path.join(directory, filename)

    def publish(self, base_url):
        logging.info('Convert: %s' % self.path)

        if self.extension == ".md":
            target_path = os.path.join(self.directory, self.basename + ".html")
            md = markdown.Markdown(extensions=['meta', 'fenced_code', 'codehilite', 'footnotes', 'tables'])

            # Convert markdown
            with codecs.open(self.path, "r", encoding="utf-8") as input_file:
                body = md.convert(input_file.read())

            # Get page title from metadata otherwise use filename
            title = self.basename
            if 'title' in md.Meta:
                title = md.Meta['title'][0]
                print title

            # Generate index page, if indicated in the metadata
            index = ''
            if 'index' in md.Meta:
                logging.info("Generating index page")

                template_name = "index_entry.jinja"
                template = jinja_env.get_template(template_name)

                docs = []
                for f in glob.glob(os.path.join(self.directory, "*.md")):
                    doc = IndexedDocument(f)
                    if doc.valid:
                        docs.append(doc)

                date_doc = [(dateutil.parser.parse(doc.date), doc) for doc in docs]


                for date, doc in sorted(date_doc, reverse=True):
                    index += template.render({"title": doc.title, "summary": doc.summary, "date": doc.date, "filename": doc.basename+".html"})

            # Load template
            template_name = "default.jinja"
            if 'template' in md.Meta:
                template_name = md.Meta['template'][0]
            template = jinja_env.get_template(template_name)
            html = template.render({"body": body, "base_url": base_url, "title": title, "index": index})

            # Save the generate HTML
            with codecs.open(target_path, "w+", encoding="utf-8") as output_file:
                output_file.write(html)

class FileEventHandler(watchdog.events.FileSystemEventHandler):
    """Publish HTML in response to updates to the file system"""
    def __init__(self, source_dir, base_url):
        self.source_dir = source_dir
        self.base_url = base_url

    def on_any_event(self, event):
        self.publish()

    def publish(self):
        logging.info("Reconvert source directory...")
        for root, dirs, files in os.walk(self.source_dir):
            for filename in files:
                doc = Document(root, filename)
                doc.publish(self.base_url)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Corrupt the media and then lie about it')
    parser.add_argument('source', type=unicode, help='Source directory')
    parser.add_argument('--base_url', type=unicode, help='Base url')
    args = parser.parse_args()

    base_dir = os.getcwd()
    source_dir = os.path.join(base_dir, args.source)
    base_url = args.base_url or base_dir

    # Initialise jinja
    template_loader = jinja2.FileSystemLoader(searchpath="templates")
    jinja_env = jinja2.Environment(loader=template_loader)

    # Monitor file system and re-publish on filesystem changes
    handler = FileEventHandler(source_dir, base_url)
    handler.publish()
    observer = Observer()
    observer.schedule(handler, path=base_dir, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()
