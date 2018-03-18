#!/usr/bin/env python
# encoding=utf-8

'''
Crawl online novel to local file starting with a toc page.
'''

import os
import sys
import re
import time
import argparse
import os.path as path
import urllib.request
import urllib.parse as urlparse
from html.parser import HTMLParser
from multiprocessing.dummy import Pool

# DO NOT USE os.linesep when writing files.
LINE_ENDING = '\n'

# user messages
MSG_DOWNLOADING_TOC_PAGE = '正在下载目录页...'
MSG_TOC_NOT_FOUND = '目录未找到'
MSG_DOWNLOADING_TEXT = '正在下载正文...'
MSG_EXPORTING_TOC = '正在导出目录...'
MSG_EXPORTING = '正在导出...'
MSG_CHAPTER_OK = '[OK]'
MSG_CHAPTER_NA = '[NA]'

def get_args():
    ap = argparse.ArgumentParser('Crawl online novel to local file.')
    ap.add_argument('--dump-toc', action = 'store_true', help = 'dump table of content only')
    ap.add_argument('--thread-num', type=int, default=64, help='number of threads to grab chapters')
    ap.add_argument('--page-encoding', default='gbk', help='html page encoding')
    ap.add_argument('--page-timeout', type=int, default=30, help='page timeout in seconds, default is 30')
    ap.add_argument('--page-retry', type=int, default=3, help='retry times to download page on failing, default is 3')
    ap.add_argument('--file-encoding', default='utf-8', help='encoding of book, default is utf-8')
    ap.add_argument('title', help='book title')
    ap.add_argument('url', help='url of content page')

    return ap.parse_args()

def request_page(url, timeout):
    # use browser agent to avoid being a robot
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
    req = urllib.request.Request(url)
    req.add_header('User-Agent',user_agent)
    response = urllib.request.urlopen(req, timeout=timeout)
    page = response.read()
    return page

def download_page(url, timeout, retry):
    repeat = 0
    page = None

    while not page:
        try:
            page = request_page(url, timeout)
        except Exception as e:
            repeat += 1
            if repeat < retry:
                time.sleep(1)
            else:
                raise

    return page

class TOCE_Link(HTMLParser):
    '''
    Extract toc from all links.
    It assumes that chapter links are consecutive and regular.
    '''
    A = 'a'
    HREF = 'href'

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=False)

        self.tags = []      # stack of opened tags
        self.toc = []       # extracted toc, (head, url)
        self.href = None    # href attr of current <a> label

    def extract(self, html):
        self.feed(html)
        self.filter()
        return self.toc

    def filter(self):
        '''
        figure out the actual toc items by uh, guess.
        rule:
        + toc links are relative paths to page url, e.g. '1234/5678.html'.
        + toc links have the same basepath, e.g. '1234' above.
        + basepath of toc links is different from ones of other links.
        + toc links are consecutive.
        + group links by basepath and pick the largest group as the result.
        '''
        class compound: pass
        groups = []

        # group links
        for i, (name, url) in enumerate(self.toc):
            basepath = path.dirname(url)
            if not groups or groups[-1].basepath != basepath:
                g = compound()
                g.idx = i
                g.basepath = basepath
                g.cnt = 1
                groups.append(g)
            else:
                groups[-1].cnt += 1

        # pick group which has most members
        if groups:
            g = max(groups, key=lambda g: g.cnt)
            i = g.idx
            j = g.idx + g.cnt
            self.toc = self.toc[i:j]

    def is_in_a(self):
        return self.tags and self.tags[-1] == TOCE_Link.A

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == TOCE_Link.A:
            for k, v in attrs:
                if k == TOCE_Link.HREF:
                    self.href = v.strip()
                    break
            else:   # indent as for statement
                self.href = None
            if not urlparse.urlparse(self.href).path:
                # it seems not a normal href, e.g. an anchor '#bottom'
                self.href = None

    def handle_endtag(self, tag):
        if self.tags:
            self.tags.pop()

    def handle_data(self, data):
        cleandata = data.strip()
        if cleandata and self.href and self.is_in_a():
            self.toc.append((cleandata, self.href))

class TE_DivContent(HTMLParser):
    '''
    Extract chapter text from <div> label.
    It assumes that the longest div content is the text.
    '''
    DIV = 'div'
    BR = 'br'

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=False)

        self.tags = []      # stack of opened tags
        self.text = ''      # final result, the longest div content
        self.current = ''   # content of current div

    def extract(self, html):
        self.feed(html)
        return self.text

    def is_in_div(self):
        return self.tags and self.tags[-1] == TE_DivContent.DIV

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)

    def handle_endtag(self, tag):
        if self.tags:
            self.tags.pop()

        if tag == TE_DivContent.DIV:
            # closing a div, pick the longest one
            if len(self.current) > len(self.text):
                self.text = self.current
            # reset current
            self.current = ''
        elif tag == TE_DivContent.BR and self.is_in_div():
            # translate <br /> to new line
            self.current += LINE_ENDING

    def handle_data(self, data):
        cleandata = data.strip()
        if cleandata and self.is_in_div():
            self.current += cleandata

def get_toc(url, encoding, timeout, retry):
    page = download_page(url, timeout, retry)
    html = page.decode(encoding)

    # try each toc extractor
    toc_exractors = [
        TOCE_Link,
    ]
    for toce in toc_exractors:
        toc = toce().extract(html)
        if toc:
            break

    toc = [(head, urlparse.urljoin(url, path)) for head, path in toc]

    return toc

def get_text(toc, thread_num, encoding, timeout, retry):
    chapters = []
    for head, url in toc:
        chapters.append((
                    head,
                    url,
                    encoding,
                    timeout,
                    retry,
            ))

    with Pool(thread_num) as pool:
        text = pool.map(get_chapter, chapters)

    return text

def get_chapter(chapter):
    head, url, encoding, timeout, retry = chapter

    page = download_page(url, timeout, retry)
    html = page.decode(encoding)

    # try each text extractor
    text_exractors = [
        TE_DivContent,
    ]
    for te in text_exractors:
        text = te().extract(html)
        if text:
            break

    flag = MSG_CHAPTER_OK if text else MSG_CHAPTER_NA
    print('%s %s' % (flag, head))

    return (head, text)

def export_toc(toc, title, file_encoding):
    with open('%s_toc.txt' % title, mode='w', encoding=file_encoding) as fd:
        for head, url in toc:
            fd.write(head + ' ' + url)
            fd.write(LINE_ENDING)

def export_file(text, title, file_encoding):
    with open('%s.txt' % title, mode='w', encoding=file_encoding) as fd:
        for head, text in text:
            fd.write(head)
            fd.write(LINE_ENDING*2)
            fd.write(text)
            fd.write(LINE_ENDING*2)

def time_report(interval):
    SECOND_PER_HOUR = 60 * 60
    SECOND_PER_MINUTE = 60

    h = interval // SECOND_PER_HOUR
    interval %= SECOND_PER_HOUR

    m = interval // SECOND_PER_MINUTE
    interval %= SECOND_PER_MINUTE

    s = interval

    report = '用时'
    if h > 0:
        report += str(h)
        report += '小时'
    if m > 0:
        report += str(m)
        report += '分'
    if s > 0 or h+m == 0:
        report += str(s)
        report += '秒'

    return report

def crawl(args):
    print(MSG_DOWNLOADING_TOC_PAGE)
    toc = get_toc(args.url,
                args.page_encoding,
                args.page_timeout,
                args.page_retry)

    if not toc:
        print(MSG_TOC_NOT_FOUND)
        return

    if args.dump_toc:
        print(MSG_EXPORTING_TOC)
        export_toc(toc, args.title, args.file_encoding)
        return

    print(MSG_DOWNLOADING_TEXT)
    text = get_text(toc,
        args.thread_num,
        args.page_encoding,
        args.page_timeout,
        args.page_retry)

    print(MSG_EXPORTING)
    export_file(text, args.title, args.file_encoding)

if __name__ == '__main__':
    start = time.time()
    args = get_args()
    crawl(args)
    elapsed = int(time.time()-start)
    report = time_report(elapsed)
    print(report)
