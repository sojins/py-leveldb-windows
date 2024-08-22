# encoding: utf-8
from setuptools import setup, find_packages, Extension

if __name__ == '__main__':
    leveldb_module = Extension('leveldb', 
                       include_dirs = [r'../../leveldb',r'../../leveldb/include', r'../../snappy', r'D:\References\Python-3.8.12\Include'],
                       libraries = ['static_leveldb32'],
                       library_dirs = [r'lib32', r'D:\References\Python-3.8.12\PCbuild\win32'],
                       sources=[r'../leveldb_object.cc', r'../leveldb_ext.cc'],
                       )
    setup(
        name='FdLevelDB',
        version='1.0.0.1',
        description='Google LevelDB using Python by FINALDATA',
        long_description='Google LevelDB using Python by FINALDATA',
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
        ext_modules=[leveldb_module]
    )
