# The MIT License (MIT)
# Copyright (c) 2016 東京大学アイドル同好会
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from pymongo import MongoClient
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib as mpl
import matplotlib.pyplot as plt
import MeCab
from requests_oauthlib import OAuth1Session
from requests.exceptions import ConnectionError, ReadTimeout, SSLError
import json, datetime, time, pytz, re, sys, traceback, pymongo
import os

KEYS = {
    'consumer_key': os.environ['CONSUMER_KEY'],
    'consumer_secret': os.environ['CONSUMER_SECRET'],
    'access_token': os.environ['ACCESS_TOKEN'],
    'access_secret': os.environ['ACCESS_SECRET']
}

twitter = None
client = None
db = None
tweet_data = None
meta = None

def prepare_directory():
    if not os.path.exists('texts'):
        os.mkdir('texts')
    if not os.path.exists('word_dics'):
        os.mkdir('word_dics')
    if not os.path.exists('figs'):
        os.mkdir('figs')

def save_all_user_tweets(screen_names):
    for screen_name in screen_names:
        initialize(screen_name)

        sid = -1
        mid = -1
        count = 0

        print("Start to save tweets of {}".format(screen_name))

        res = None
        while (True):
            try:
                count = count + 1
                sys.stdout.write('%d, ' % count)
                res = get_user_tweets(screen_name, max_id=mid, since_id=sid)
                if res['result'] == False:
                    print('status_code {}'.format(res['status_code']))
                    print('result: {}'.format(res))
                    break
                if int(res['limit'] == 0):
                    print('Adding created_at field.')
                    for d in tweet_data.find({'created_datetime': {'$exists': False}}, {'_id': 1, 'created_at': 1}):
                        tweet_data.update({'_id': d['_id']},
                                          {'$set': {'created_datetime': str_to_date_jp(d['created_at'])}})
                    diff_sec = int(res['reset_time_unix']) - now_unix_time()
                    print('sleep {} sec.'.format(diff_sec + 5))
                    if diff_sec > 0:
                        time.sleep(diff_sec + 5)
                else:
                    if len(res['statuses']) == 0:
                        sys.stdout.write('statuses is none. ')
                        break
                    else:
                        for s in res['statuses']:
                            try:
                                tweet_data.insert(s)
                            except pymongo.errors.DuplicateKeyError as e:
                                print('duplicate key')
                        pattern = r'.*max_id=([0-9]*)\&.*'
                        mid = res['statuses'][-1]['id'] - 1

            except SSLError as e:
                print('SSLError({0})ß'.format(e))
                print('waiting 5mins')
                time.sleep(5 * 60)
            except ConnectionError as e:
                print('waiting 5mins')
                time.sleep(5 * 60)
            except ReadTimeout as e:
                print('waiting 5mins')
                time.sleep(5 * 60)
            except:
                print('Unexpected error:', sys.exc_info()[0])
                traceback.format_exc(sys.exc_info()[2])
                raise
            finally:
                info = sys.exc_info()
                print(info)


def initialize(screen_name):  # twitter接続情報や、mongoDBへの接続処理等initial処理実行
    global twitter, twitter, client, db, tweet_data, meta
    twitter = OAuth1Session(KEYS['consumer_key'], KEYS['consumer_secret'],
                            KEYS['access_token'], KEYS['access_secret'])
    client = MongoClient('localhost', 27017)
    db = client['{}'.format(screen_name)]
    db.tweet.ensure_index('id', unique=True)
    tweet_data = db.tweet
    meta = db.metadata


def get_user_tweets(screen_name, max_id=-1, since_id=-1):
    global twitter
    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {
        'screen_name': screen_name,
        'count': '200',
        'include_rts': 'false',
        'exclude_replies': 'false',
    }
    if max_id != -1:
        params['max_id'] = max_id
    if since_id != -1:
        params['since_id'] = since_id

    print('mid: {0}, sid: {1}'.format(max_id, since_id))

    req = twitter.get(url, params=params)

    if req.status_code == 200:
        timeline = json.loads(req.text)
        statuses = timeline
        limit = req.headers['x-rate-limit-remaining'] if 'x-rate-limit-remaining' in req.headers else 0
        reset = req.headers['x-rate-limit-reset'] if 'x-rate-limit-reset' in req.headers else 0
        return {'result': True, 'statuses': statuses, 'limit': limit,
                'reset_time': datetime.datetime.fromtimestamp(float(reset)), 'reset_time_unix': reset}
    else:
        print('Error: %d' % req.status_code)
        return {'result': False, 'status_code': req.status_code}


def str_to_date_jp(str_date):
    dts = datetime.datetime.strptime(str_date, '%a %b %d %H:%M:%S +0000 %Y')
    return pytz.utc.localize(dts).astimezone(pytz.timezone('Asia/Tokyo'))


# 現在時刻をUNIX Timeで返す
def now_unix_time():
    return time.mktime(datetime.datetime.now().timetuple())


def get_tweets(screen_name, from_time_str=None, to_time_str=None):
    client = MongoClient('localhost', 27017)
    db = client['{}'.format(screen_name)]
    tweets = db['tweet'].find({})
    df = pd.DataFrame(list(tweets))
    df['point'] = df['favorite_count'] + df['retweet_count']
    df['created_at'] = df['created_at'].map(lambda x: datetime.datetime.strptime(x, '%a %b %d %H:%M:%S %z %Y'))
    if from_time_str:
        from_time = datetime.datetime.strptime(from_time_str, '%Y/%m/%d %H:%M:%S %z')
        df = df[df['created_at'] > from_time]
    if to_time_str:
        to_time = datetime.datetime.strptime(to_time_str, '%Y/%m/%d %H:%M:%S %z')
        df = df[df['created_at'] < to_time]
    return df


def get_tweets_include_word(screen_name, word, from_time_str=None, to_time_str=None):
    client = MongoClient('localhost', 27017)
    db = client['{}'.format(screen_name)]
    tweets = db['tweet'].find({})
    df = pd.DataFrame(list(tweets))
    df['point'] = df['favorite_count'] + df['retweet_count']
    df['created_at'] = df['created_at'].map(lambda x: datetime.datetime.strptime(x, '%a %b %d %H:%M:%S %z %Y'))
    if from_time_str:
        from_time = datetime.datetime.strptime(from_time_str, '%Y/%m/%d %H:%M:%S %z')
        df = df[df['created_at'] > from_time]
    if to_time_str:
        to_time = datetime.datetime.strptime(to_time_str, '%Y/%m/%d %H:%M:%S %z')
        df = df[df['created_at'] < to_time]
    return df[df['text'].str.find(word) >= 0], df[df['text'].str.find(word) < 0]


def get_all_tweets_include_word(screen_names, word, from_time_str=None, to_time_str=None):
    tweets_include = None
    tweets_not_include = None
    for screen_name in screen_names:
        p, n = get_tweets_include_word(screen_name, word, from_time_str, to_time_str)
        if not p.empty:
            tweets_include = pd.concat([tweets_include, p])
        if not n.empty:
            tweets_not_include = pd.concat([tweets_not_include, n])
    return tweets_include, tweets_not_include


def get_all_tweets(screen_names, from_time_str=None, to_time_str=None):
    tweets = None
    for screen_name in screen_names:
        if not t.empty:
            t = get_tweets(screen_name, from_time_str, to_time_str)
        tweets = pd.concat([tweets, t])
    return tweets


def plot_boxes_of_parameters(word, data_list, prefix):
    plot_boxes([data_list[1]['favorite_count'], data_list[0]['favorite_count']],
               'figs/{}_box_fav.png'.format(prefix),
               '「{}」という単語を'.format(word),
               'いいね数')
    plot_boxes([data_list[1]['retweet_count'], data_list[0]['retweet_count']],
               'figs/{}_box_rt.png'.format(prefix),
               '「{}」という単語を'.format(word),
               'リツイート数')
    plot_boxes([data_list[1]['point'], data_list[0]['point']], 'figs/{}_box_point.png'.format(prefix),
               '「{}」という単語を'.format(word),
               'つぶやき係数')


def plot_boxes(data, file_name, xlabel=None, ylabel=None):
    mpl.rcParams['font.family'] = 'Osaka'
    fig = plt.figure()
    ax = fig.add_subplot(111)
    bp = ax.boxplot(data, 0, '', patch_artist=True)
    ax.set_xticklabels(['含まない', '含む'])
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)
    for box in bp['boxes']:
        box.set(color='#0074bf', linewidth=2)
        box.set(facecolor="#65ace4")

    for whisker in bp['whiskers']:
        whisker.set(color='#0074bf', linewidth=2)

    for cap in bp['caps']:
        cap.set(color='#0074bf', linewidth=2)

    for median in bp['medians']:
        median.set(color='#9460a0', linewidth=2)
    plt.savefig(file_name)
    plt.close()


def conduct_ttest(data0, data1, title=""):
    t, p = stats.ttest_ind(np.array(data0), np.array(data1), equal_var=False)
    print(title)
    print("T: {}".format(t))
    print("P: {}".format(p))


def plot_bar(data_list, ylabel=None, data_name=None):
    mpl.rcParams['font.family'] = 'Osaka'
    x = np.array([0, 1, 2, 3, 4])
    plt.bar(x, np.array(data_list), align='center', color='#65ace4')
    plt.xticks(x, ['10', '11', '12', '1', '2'])
    plt.xlabel('月')
    plt.ylabel(ylabel)
    plt.savefig('figs/member_bar_{}.png'.format(data_name))


def plot_mean_month(key, time_points):
    means = []
    for i in range(len(time_points) - 1):
        p_tweets, n_tweets = get_all_tweets_include_word(screen_names, word, time_points[i],
                                                         time_points[i + 1])
        means.append(n_tweets[key].mean())
    plot_bar(means, 'いいね数', 'favorite')


def save_tweets_into_file(screen_name, from_time_str=None, to_time_str=None):
    tweet_df = get_tweets(screen_name, from_time_str, to_time_str)
    with open('texts/{}_tweet.txt'.format(screen_name), 'w', encoding='utf-8') as f:
        tweet_df['text'].apply(lambda x: f.write(x + '\n'))


def save_all_tweets_into_file(screen_names, from_time_str=None, to_time_str=None):
    for screen_name in screen_names:
        save_tweets_into_file(screen_name, from_time_str, to_time_str)


def create_words_dictionary(screen_name):
    with open('texts/{}_tweet.txt'.format(screen_name), 'r', encoding='utf-8') as f:
        data = f.read()
        mecab = MeCab.Tagger("-Ochasen -d /usr/local/lib/mecab/dic/mecab-ipadic-neologd/")
        node = mecab.parseToNode(data)
        phrases = node.next
        dict = {}
        while phrases:
            try:
                k = node.surface
                node = node.next
                if dict.get(k) is not None:
                    dict[k] = dict[k] + 1
                else:
                    dict[k] = 1
            except AttributeError:
                break
            except UnicodeDecodeError:
                node = node.next
                continue
        return dict


def create_norm_dictionary(screen_name):
    with open('texts/{}_tweet.txt'.format(screen_name), 'r', encoding='utf-8') as f:
        data = f.read()
        mecab = MeCab.Tagger("-Ochasen -d /usr/local/lib/mecab/dic/mecab-ipadic-neologd/")
        node = mecab.parseToNode(data)
        phrases = node.next
        norm = {}
        while phrases:
            try:
                k = node.surface
                node = node.next
                if node.feature.split(',')[1] == "固有名詞":
                    if norm.get(k) is not None:
                        norm[k] = norm[k] + 1
                    else:
                        norm[k] = 1
            except AttributeError:
                break
        return norm


def save_word_dic_into_file(screen_name, dict):
    with open('word_dics/{}_twitter.csv'.format(screen_name), 'w', encoding='utf-8') as f:
        f.write('word,count\n')
        for k, v in reversed(sorted(dict.items(), key=lambda x: x[1])):
            f.write('{},{}\n'.format(k, v))


def save_all_word_dic_file(screen_names):
    for screen_name in screen_names:
        dict = create_words_dictionary(screen_name)
        save_word_dic_into_file(screen_name, dict)


def save_all_norm_dif_file(screen_names):
    for screen_name in screen_names:
        norm = create_norm_dictionary(screen_name)
        save_word_dic_into_file(screen_name, norm)
        print("Norm Dic Created: {}".format(screen_name))


if __name__ == "__main__":
    screen_names = [
        'AOP_animelove',
        'sakuranarisa',
        'sasaodoru',
        'mizuki__aoi',
        'hiroseyuuki',
        'kei_tomoe',
        'fukuoyui',
    ]

    word = 'おそ松さん'
    start_time = '2015/10/01 00:00:00 +0900'
    end_time = '2016/3/1 00:00:00 +0900'

    time_points = [
        '2015/10/01 00:00:00 +0900',
        '2015/11/01 00:00:00 +0900',
        '2015/12/01 00:00:00 +0900',
        '2016/01/01 00:00:00 +0900',
        '2016/02/01 00:00:00 +0900',
        '2016/03/01 00:00:00 +0900',
    ]

    prepare_directory()

    # Load tweets from Twitter API
    save_all_user_tweets(screen_names)

    # get tweets of member accounts
    member_tweets = get_all_tweets_include_word(screen_names[1:], word, start_time, end_time)

    # t test
    conduct_ttest(member_tweets[0]['favorite_count'], member_tweets[1]['favorite_count'], "Member Favorite")
    conduct_ttest(member_tweets[0]['retweet_count'], member_tweets[1]['retweet_count'], "Member Retweet")

    # plot monthly favorites
    plot_mean_month('favorite_count', time_points)

    # plot box of favorites, retweets and sum of them.
    plot_boxes_of_parameters(word, member_tweets, 'member')

    # save tweets into a file
    save_all_tweets_into_file(screen_names, start_time, end_time)

    # create dictionary using MeCab
    save_all_norm_dif_file(screen_names)
