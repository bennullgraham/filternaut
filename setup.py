from setuptools import setup

setup(
    name='django-filternaut',
    version='0.0.9',
    author='Ben Graham',
    author_email='bgraham@bgraham.com.au',
    description=('Construct arbitrarily complex Django "Q" filters from flat '
                 'data, such as query parameters.'),
    long_description=open('README.rst').read(),
    url='http://github.com/bennullgraham/django-filternaut/',
    license='BSD',
    packages=['filternaut'],
    install_requires=['six>=1.9.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'Framework :: Django',
    ],
)
