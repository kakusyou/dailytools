#!/usr/bin/env python
# encoding=utf-8

'''
Group baby's photos by his/her month age.
'''

import os
import sys
import shutil
import argparse
from datetime import date
from datetime import datetime
from datetime import timedelta

import exifread

def str2date(datestr):
    try:
        return datetime.strptime(datestr, r'%Y-%m-%d').date()
    except Exception as e:
        msg = '%s is not a valid date.' % datestr
        raise argparse.ArgumentTypeError(msg)

def get_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--birth-date', required=True, type=str2date, help="baby's birth date like 2016-1-1")
    ap.add_argument('photo_dir', help='photo directory')
    ap.add_argument('dest_dir', help='where grouped photos to be copied to')

    return ap.parse_args()

def calc_month_age(theday, birthdate):
    '''Calculate month age for theday'''
    if theday < birthdate:
        return -1
    elif theday == birthdate:
        return 0
    else:
        yeard = theday.year - birthdate.year
        monthd = theday.month - birthdate.month
        corrector = -1 if birthdate.day > theday.day else 0

        return yeard*12 + monthd + corrector

def calc_birthday_by_month_age(month_age, birthdate):
    '''
    Calculate birthday given by birth date and age in month.
    eg.
    birthdate: 2017-1-17
    age in month: 2
    the birthday is 2017-3-17
    '''
    year = birthdate.year
    month = birthdate.month + month_age
    day = birthdate.day

    if month < 1 or month > 12:
        year += ((month-1)//12)
        month = ((month-1)%12+1)

    agedate = None

    # normalize date, such as change 2015-17-01 to 2016-05-01.
    while True:
        try:
            agedate = date(year, month, day)
            break
        except:
            day -= 1
            continue

    return agedate

def get_image_datetime(image):
    '''
    Read DateTimeOriginal tag in EXIF as taken time of photo.
    If DateTimeOriginal is not found, use modify time of file instead.
    '''
    TAG_DATETAKEN = 'EXIF DateTimeOriginal'
    try:
        with open(image, 'rb') as f:
            tags = exifread.process_file(f)
            datetaken = str(tags[TAG_DATETAKEN])
            dttaken = datetime.strptime(datetaken, '%Y:%m:%d %H:%M:%S')
            return dttaken
    except FileNotFoundError as e:
        return None
    except:
        pass

    try:
        mtime = os.path.getmtime(image)
        return datetime.fromtimestamp(mtime)
    except:
        return None

def get_group_dir_name(age, birthdate):
    datefmt = r'%Y%m%d'
    prebirthdir = r'prebirth'
    monthagedir = r'%d个月_%s_%s'
    if age < 0:
        targetdir = prebirthdir
    else:
        startday = calc_birthday_by_month_age(age, birthdate)
        endday = calc_birthday_by_month_age(age+1, birthdate) - timedelta(1)
        targetdir = monthagedir % (age, startday.strftime(datefmt), endday.strftime(datefmt))
    return targetdir

def group_by_month_age(imgdir, outdir, birthdate):
    '''
    Group images in imgdir by age in month.
    it first creates directories for each group in outdir named as '0个月_20150423_20150522',
    and then copy images to corresponding directories.
    '''
    agedir = {}

    try:
        for entry in os.scandir(imgdir):
            if not entry.is_file(follow_symlinks=False):
                continue
            name = entry.name
            image = entry.path
            print(name, end='')   # no new line for possible error message later.
            datetimetaken = get_image_datetime(image)
            if not datetimetaken:
                print(': failed to get DateTaken')
                continue
            datetaken = datetimetaken.date()
            age = calc_month_age(datetaken, birthdate)
            targetdir = agedir.get(age)
            if not targetdir:
                targetdir = get_group_dir_name(age, birthdate)
                targetdir = os.path.join(outdir, targetdir)
                try:
                    os.mkdir(targetdir)
                except FileExistsError as e:
                    agedir[age] = targetdir
                    pass # targetdir already exists
                except Exception as e:
                    print(': %s', e)
                    continue
                else:
                    agedir[age] = targetdir

            try:
                shutil.copy2(image, targetdir)
            except Exception as e:
                print(': %s', e)
                continue

            print()     # line feed for printing of next image
    except FileNotFoundError as e:
        print('%s is not found' % e.filename)
    except NotADirectoryError as e:
        print('%s is not a directory' % e.filename)
    except PermissionError as e:
        print('%s is permission denied' % e.filename)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    args = get_args()
    group_by_month_age(args.photo_dir,
                        args.dest_dir,
                        args.birth_date)
