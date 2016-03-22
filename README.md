アイドルゼミ
====

## 概要

KawaiianTV 内の番組「現役大学生が完全プロデュース アイドルゼミ」の東京大学アイドル同好会担当回で使用したアイドル分析プログラムのソースコードを紹介するためのリポジトリです.

## 依存環境

- Python3
- [Anaconda](https://www.continuum.io/why-anaconda)
- [MeCab](http://mecab.googlecode.com/svn/trunk/mecab/doc/index.html?sess=3f6a4f9896295ef2480fa2482de521f6)
- [mecab-ipadic-NEologd](https://github.com/neologd/mecab-ipadic-neologd)

## 使用法

#### Twitter API の各種認証情報を環境変数に登録(ソースコードに直接書き込むのも可)

```shell
export CONSUMER_KEY=""
export CONSUMER_SECRET=""
export ACCESS_TOKEN=""
export ACCESS_SECRET=""
```

#### Twitter分析

```Python3
from twitteranalysis import *

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
```

#### Blog分析

 ```Python3
 from bloganalysis import *

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
     crawl_blog(blog_id, 100, "ameba")

 for blog_id in blog_ids:
     dict = create_norm_dictionary(blog_id)
     save_word_dic_into_file(blog_id, dict)
 ```

## ライセンス
- MIT
    - see LICENSE
