from setuptools import setup

setup(name='cocord232',
      version='0.1',
      description='GE Concord 4 Interface Library and Server',
      author='Jason Carter',
      author_email='jason@jason-carter.net',
      url='http://github.com/JasonCarter80/cocord232',
      packages=['concord232'],
      install_requires=['requests', 'stevedore', 'prettytable', 'pyserial', 'flask'],
      scripts=['cocord_server', 'concord_client'],
  )
