# 概要

将宝宝的照片按照月龄分组，建立相应的目录并拷入其中，便于归档。
照片对应的月龄通过拍摄日期和出生日期来计算。

照片拍摄日期依次尝试如下方法来获取：
1. EXIF中的DateTimeOriginal标签
1. 文件的修改时间

# 要求

+ Python 3.5及以上
+ exifread \
  `pip install exifread`

# 用法

> ./sortphotos.py [-h] --birth-date BIRTH_DATE photo_dir dest_dir

+ *-h* \
  显示帮助。
+ *--birth-date* \
  宝宝出生日期，用以计算照片对应的月龄，格式为`2016-1-1`。
+ *photo_dir* \
  待分组照片所在目录，不检查文件类型，所有文件都当作照片处理。
+ *dst_dir* \
  存放分组后的照片。

# 示例

```bash
$ ./sortphotos.py --birth-date 2016-1-1 myphotos archive
IMG_4066.JPG
IMG_4118.JPG
IMG_4632.JPG
```

运行之后，`myphotos`下的照片会按照月龄分组，并复制到`archive`相应子目录下。

```
archive
├── 0个月_20160101_20160131/
└── 1个月_20160201_20160229/
```
