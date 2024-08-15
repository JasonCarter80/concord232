from setuptools import setup

setup(
    name='concord232',
    version='0.15.1',
    description='GE Concord 4 RS232 Serial Interface Library and Server',
    author='Jason Carter',
    author_email='jason@jason-carter.net',
    url='http://github.com/JasonCarter80/concord232',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=['concord232'],
    install_requires=['requests', 'stevedore', 'prettytable', 'pyserial', 'flask'],
    scripts=['concord232_server', 'concord232_client'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ]
)
