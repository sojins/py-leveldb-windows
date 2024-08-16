# encoding: utf-8
from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='FdLevelDB',
        version='1.0.0.0',
        description='Google LevelDB using Python by FINALDATA',
        url='package_url',
        install_requires=[
        ],
        author='Kate Choi',
        author_email='sojins@finaldata.com',
        license='MIT',
        packages=find_packages(exclude=[]),
        python_requires='>=3.8',
        # package_dir={'': 'src'},
        package_dir={'FdLevelDB': 'FdLevelDB'},
        zip_safe=False,
        include_package_data=True,
        package_data={'': ['*.pyd', 'utils/*']},
    )
