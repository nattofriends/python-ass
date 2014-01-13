from setuptools import setup, find_packages

setup(
    name = 'ass',
    version = '0.2.2',
    description='A library for parsing and manipulating Advanced SubStation Alpha subtitle files.',
    author='Tony Young',
    author_email='tony@rfw.name',
    keywords='ass subtitle substation alpha',
    packages = ['ass'],
    url = 'http://github.com/rfw/python-ass',
    license = 'MIT',
    classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 3',
    'Topic :: Multimedia :: Video',
    'Topic :: Software Development :: Libraries',
    'Topic :: Text Processing :: Markup'],
    install_requires = ['setuptools'],
    zip_safe=True)
