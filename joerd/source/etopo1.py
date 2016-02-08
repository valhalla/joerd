from joerd.util import BoundingBox
from joerd.download import get as joerd_get
from contextlib import closing
from shutil import copyfile
import os.path
import os
import requests
import logging
import re
import tempfile
import sys
import zipfile
import traceback
import subprocess
import glob
from osgeo import gdal
from time import sleep


WGS84_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,' \
            '298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0]' \
            ',AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY[' \
            '"EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY[' \
            '"EPSG","9108"]],AUTHORITY["EPSG","4326"]]'


def _check_zip_file(tmp):
    try:
        zip_file = zipfile.ZipFile(tmp.name, 'r')
        test_result = zip_file.testzip()
        return test_result is None

    except:
        pass

    return False


def _exponential_backoff(try_num):
    secs = min((1 << try_num) - 1, 600)
    sleep(secs)


def _download_etopo1_file(target_name, base_dir, url):
    output_file = os.path.join(base_dir, target_name)

    if os.path.isfile(output_file):
        return output_file

    with joerd_get(url, dict(verifier=_check_zip_file, tries=10,
                             backoff=_exponential_backoff)) as tmp:
        with zipfile.ZipFile(tmp.name, 'r') as zfile:
            zfile.extract(target_name, base_dir)

    return output_file


class ETOPO1:

    def __init__(self, options={}):
        self.base_dir = options.get('base_dir', 'etopo1')
        self.etopo1_url = options['url']

    def download(self):
        logger = logging.getLogger('etopo1')
        logger.info("Starting ETOPO1 download, this may take some time...")
        file = _download_etopo1_file('ETOPO1_Bed_g_geotiff.tif',
                                     self.base_dir, self.etopo1_url)
        assert os.path.isfile(file)
        logger.info("Download complete.")

    def buildvrt(self):
        logger = logging.getLogger('etopo1')
        logger.info("Creating VRT.")

        # ETOPO1 covers the whole world
        files = glob.glob(os.path.join(self.base_dir, '*.tif'))

        args = ["gdalbuildvrt", "-q", "-a_srs", WGS84_WKT, \
                self.vrt_file()] + files
        status = subprocess.call(args)

        if status != 0:
            raise Exception("Call to gdalbuildvrt failed: status=%r" % status)

        assert os.path.isfile(self.vrt_file())

        logger.info("VRT created.")

    def vrt_file(self):
        return os.path.join(self.base_dir, "etopo1.vrt")

    def mask_negative(self):
        return False

    def filter_type(self, src_res, dst_res):
        return gdal.GRA_Lanczos


def create(regions, options):
    return ETOPO1(options)
