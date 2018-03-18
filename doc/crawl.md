# 概述

从一个目录页开始抓取在线小说到本地文件。

内部抓取流程如下：
1. 分析目录页面，提取各章节标题及地址；
1. 并发访问各章节页面并提取正文；
1. 按章节顺序写入文件，章节顺序以其在目录页面中出现的顺序为准。

该工具通过对页面源码进行分析猜测来识别目录及正文，所以有一定的局限性：
+ 特殊页面无法抓取（如以图片形式呈现的页面）
+ HTML不规范的页面，目录及正文可能识别错误

# 要求

+ Python 3.5及以上

# 用法

> ./crawl.py [-h] [--dump-toc] [--thread-num THREAD_NUM] [--page-encoding PAGE_ENCODING] [--page-timeout PAGE_TIMEOUT] [--page-retry PAGE_RETRY] [--file-encoding FILE_ENCODING] title url

+ *-h* \
    显示帮助。
+ *--dump-toc* \
    仅导出目录到文件，不抓取正文。
+ *--thread-num* \
    章节抓取并发线程数，默认`32`。
+ *--page-encoding* \
    页面编码，如`utf-8`、`gbk`等。
+ *--page-timeout* \
    页面超时时间，单位为秒，默认`30`。
+ *--page-retry* \
    页面访问失败的重试次数，默认`3`。
+ *--file-encoding* \
    保存文件的编码，取值同`--page-encoding`。
+ *title* \
    书名。导出文件默认为`{title}.txt`，如果只导出目录，则文件名为`{title}_toc.txt`。
+ *url* \
    目录页地址。

# 示例

```bash
$ ./crawl.py 某小说 http://xiaoshuo.com/12345
正在下载目录...
正在下载正文...
[OK] 第一章 标题1
[OK] 第四章 标题4
[OK] 第三章 标题3
[OK] 第二章 标题2
[OK] 第五章 标题5
正在导出...
用时5秒
```

抓取过程中会实时显示章节抓取结果：
+ *[OK]*: 抓取成功
+ *[NA]*: 抓取失败，未能识别出正文

因为是并发抓取，所以并不一定会按照章节顺序显示，但最后的文件是按章节顺序保存的。

一般情况下使用默认参数即可，如果抓取失败，可以调整相应参数再试。比如网页编码不是`gbk`时可以使用`--page-encoding`来指定。

*-END-*
