# The MIT License (MIT)
# Copyright (c) 2016 東京大学アイドル同好会
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from bs4 import BeautifulSoup
from urllib import request
from time import sleep
import MeCab
import os

def prepare_directory():
    if not os.path.exists('texts'):
        os.mkdir('texts')
    if not os.path.exists('word_dics'):
        os.mkdir('word_dics')


def crawl_blog(blog_id, page_limit, service="ameba"):
    file_path = 'texts/{}_blog.txt'.format(blog_id)
    if os.path.exists(file_path):
        os.remove(file_path)
    if service == "ameba":
        crawl_ameblo(blog_id, page_limit)
    elif service == "yahoo":
        crawl_yahoo(blog_id, page_limit)
    else:
        print("{} is not supported.".format(service))
        return


def crawl_ameblo(blog_id, page_limit):
    for page in range(page_limit):
        entry_list = 'http://ameblo.jp/{}/entrylist-{}.html'.format(blog_id, page+1)

        req = request.Request(entry_list)
        res = request.urlopen(req)
        html = res.read()
        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all('a', attrs={'class': 'contentTitle'}):
            blog_url = a.get('href')
            save_ameba_into_file(blog_url, blog_id)
            sleep(1)
        print('Page {} Finished'.format(page))


def crawl_yahoo(blog_id, page_limit):
    for page in range(page_limit):
        entry_list = 'http://blogs.yahoo.co.jp/{}/MYBLOG/yblog.html?m=lc&p={}'.format(blog_id, page)

        req = request.Request(entry_list)
        res = request.urlopen(req)
        html = res.read()
        soup = BeautifulSoup(html, "lxml")

        for h2 in soup.find_all('h2', attrs={'class': 'userDefTitle'}):
            a = h2.find('a')
            blog_url = a.get('href')
            save_yahoo_into_file(blog_url, blog_id)
            sleep(1)
        print('Page {} Finished'.format(page))


def save_ameba_into_file(url, blog_id):
    file_path = 'texts/{}_blog.txt'.format(blog_id)
    with open(file_path, 'a') as f:
        req = request.Request(url)
        res = request.urlopen(req)
        html = res.read()
        soup = BeautifulSoup(html, "lxml")
        article = soup.find('div', attrs={'class': 'articleText'})
        if article:
            article_text = article.getText()
            f.write('{}'.format(article_text))


def save_yahoo_into_file(url, blog_id):
    file_path = 'texts/{}_blog.txt'.format(blog_id)
    with open(file_path, 'a') as f:
        req = request.Request(url)
        res = request.urlopen(req)
        html = res.read()
        soup = BeautifulSoup(html, "lxml")
        article = soup.find('td', attrs={'class': 'entryTd userDefText'})
        if article:
            article_text = article.getText()
            f.write('{}'.format(article_text))


def create_norm_dictionary(blog_id):
    with open('texts/{}_blog.txt'.format(blog_id), 'r', encoding='utf-8') as f:
        data = f.read()
        mecab = MeCab.Tagger("-Ochasen -d /usr/local/lib/mecab/dic/mecab-ipadic-neologd/")
        node = mecab.parseToNode(data)
        phrases = node.next
        norm = {}
        while phrases:
            try:
                k = node.surface
                node = node.next
                if node.feature.split(',')[0] == "名詞":
                    if norm.get(k) is not None:
                        norm[k] = norm[k] + 1
                    else:
                        norm[k] = 1
            except AttributeError:
                break
            except UnicodeDecodeError:
                node = node.next
        return norm


def save_word_dic_into_file(blog_id, dict):
    with open('word_dics/{}_blog.csv'.format(blog_id), 'w', encoding='utf-8') as f:
        f.write('word,count\n')
        for k, v in reversed(sorted(dict.items(), key=lambda x: x[1])):
            f.write('{},{}\n'.format(k, v))


if __name__ == '__main__':
    blog_ids = [
        'ogino-aop',
        'sakurana-aop',
        'tomoe-aop',
        'hirose-aop',
        'fukuo-aop',
        'mizuki-aop'
    ]

    prepare_directory()

    for blog_id in blog_ids:
        crawl_blog(blog_id, 2, "ameba")

    for blog_id in blog_ids:
        dict = create_norm_dictionary(blog_id)
        save_word_dic_into_file(blog_id, dict)
