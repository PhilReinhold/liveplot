from setuptools import setup, find_packages
import py2exe

setup(
    name="liveplot",
    version="0.1",
    packages=find_packages(),
    install_requires=["PyQt4>=4.7", "pyqtgraph>=0.9"],
    author="Philip Reinhold",
    author_email="pcreinhold@gmail.com",
    license="MIT",
    keywords="plot plotting graph graphing",
    windows=[{"script":"__main__.py", "icon_resources": [(1, "icon.ico")], "dest_base":"liveplot", "other_resources":[(u"ICON", 1, open("icon.ico").read())]}],
    options={ "py2exe":
        { "includes":["scipy.sparse.csgraph._validation"],
          "dll_excludes":["MSVCP90.dll"]  }
    }
)