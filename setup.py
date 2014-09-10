from setuptools import setup, find_packages
from u115 import __version__


setup(
    name='115wangpan',
    version=__version__,
    description="Unofficial Python API wrapper for 115.com",
    long_description=open('README.rst').read(),
    keywords='115 wangpan pan cloud lixian',
    author='Shichao An',
    author_email='shichao.an@nyu.edu',
    url='https://github.com/shichao-an/115wangpan',
    license='BSD',
    install_requires=open('requirements.txt').read().splitlines(),
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
    ],
)
