from setuptools import setup, find_packages

version = '0.0.1'
name = 'endpoints-controller'


_pkg_name = name.replace('-', '_')

requirements = [
    'kubernetes',
    'kopf',
    'uvloop',
    'attrs',
    'ruamel.yaml',
]

entry_points = {
    "console_scripts": [
        # f'endpoint-controller = {_pkg_name}.main:entry',
    ]
}

setup(name=name,
      version=version,
      description="provide by ktlcove",
      long_description="",
      long_description_content_type='text/markdown',
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ],
      # url='https://github.com/ktlcove/kube-admission.git',
      author='ktlove',
      author_email='ktl_cove@126.com',
      packages=find_packages(exclude=('test', 'doc',)),
      include_package_data=True,
      zip_safe=False,
      entry_points=entry_points,
      install_requires=requirements,
      )
