from setuptools import setup
import os,glob,warnings,sys,fnmatch,subprocess
from setuptools.command.test import test as TestCommand
from distutils.core import setup
import numpy.distutils.misc_util


if sys.version_info < (3,0):
    sys.exit('Sorry, Python 2 is not supported')

class convertToArXivtest(TestCommand):

   def run_tests(self):
       import convertToArXiv
       errno = convertToArXiv.test()
       convertToArXiv.test_convertToArXiv()
       sys.exit(errno)

AUTHOR = 'Justin Pierel'
AUTHOR_EMAIL = 'justin.pierel@gmail.com'
VERSION = '0.0.1'
LICENSE = ''
URL = ''



def recursive_glob(basedir, pattern):
    matches = []
    for root, dirnames, filenames in os.walk(basedir):
        for filename in fnmatch.filter(filenames, pattern):
            matches.append(os.path.join(root, filename))
    return matches

PACKAGENAME='convertToArXiv'


# Add the project-global data
data_files = []
for dataFolderName in ['tex_files']:
  pkgdatadir = os.path.join(PACKAGENAME, dataFolderName)
  data_files.extend(recursive_glob(pkgdatadir, '*'))

data_files = [f[len(PACKAGENAME)+1:] for f in data_files]


setup(
    name=PACKAGENAME,
    cmdclass={'test': convertToArXivtest},
    setup_requires='',
    scripts=['bin/convertToArxiv'],
    install_requires=['astropy', 'pytest-astropy'],
    packages=[PACKAGENAME],
    version=VERSION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license=LICENSE,
    include_dirs=numpy.distutils.misc_util.get_numpy_include_dirs(),
    package_data={PACKAGENAME:data_files},
    include_package_data=True
)
