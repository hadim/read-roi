from setuptools import setup
from setuptools import find_packages

setup(author = 'Hadrien Mary',
	  author_email='hadrien.mary@gmail.com',
	  url = 'https://github.com/hadim/read-roi/',
	  description = 'Read ROI files .zip or .roi generated with ImageJ.',

	  packages=find_packages(),
      classifiers=[
              'Development Status :: 5 - Production/Stable',
              'Intended Audience :: Developers',
              'Natural Language :: English',
              'License :: OSI Approved :: BSD License',
              'Operating System :: OS Independent',
              'Programming Language :: Python',
              'Programming Language :: Python :: 3',
        ])
