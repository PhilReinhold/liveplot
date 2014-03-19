from setuptools import setup, find_packages

args = dict(
    name="liveplot",
    version="0.1",
    packages=find_packages(),
    install_requires=["pyqtgraph>=0.9", "pyzmq>=14.0"],
    author="Philip Reinhold",
    author_email="pcreinhold@gmail.com",
    license="MIT",
    keywords="plot plotting graph graphing",
)

try:
    import py2exe
    args.update(dict(
        windows=[{
            "script":"liveplot\\__main__.py",
            "icon_resources": [(1, "icon.ico")],
            "dest_base":"liveplot",
            }],
        options={
            "py2exe": {
                "includes":[
                    "scipy.sparse.csgraph._validation",
                    "scipy.special._ufuncs_cxx",
                    ],
                "dll_excludes":["MSVCP90.dll"]
                }
            }
        ))

except ImportError:
    print 'py2exe not found. py2exe command not available'

setup(**args)
