MESHDIFF: get the difference between topographic scans and reference STL files
====================

This is a small utility to solve the following problem:

* You are 3D-printing / precision-machining a shape from a STL file.
* You can get a topography from the object, stored as a text file containing the topography's 3D coordinates (in the original application, the topography was obtained with a line laser scanner mounted in a linear axis moving orhtogonally w.r.t. the line scanner).
* You need to measure possible differences and errors between the STL file and the result, as measured from the topography.

While not perfect, a first approximation to this problem is easy enough: just convert the topography to a STL file, and compute the difference between it and the original file. This is a small Python application that uses third-party software to solve this problem, with both command-line and GUI front-ends.

To solve the problem of computing the difference between two meshes, there are several possible solutions. One that is relatively good is [gilbo's cork](https://github.com/gilbo/cork). cork has some issues with [degenerate faces](https://github.com/gilbo/cork/issues/27) and [repeated application of boolean operations](https://github.com/gilbo/cork/issues/21), but for our particular use case is just fine, and actually better than other alternatives using floating point arithmetic. There is still one problem: cork does not accept STL files. To work around this issue, we use FreeCAD to convert STL files to OFF files and vice versa.

Examples
========

See the [wiki](https://github.com/jdfr/meshdiff/wiki) for an example. The images from that example are reproduced below:

original object: 

![original](../../wiki/images/01.STLObject.png)

topography:

![topography](../../wiki/images/03.topography.clean.png)

difference (result from using this utility):

![difference](../../wiki/images/04.difference.png)

Files
=====

* meshdiff.py contains all the logic to call FreeCAD and cork, and generate meshes from topograpic scans.

* app.py implements a command-line front-end

* gui.py implements a GUI front-end

* freecadscript.py contains the Python code to use FreeCAD (because in Windows, a separate Python executable is usually needed to use FreeCAD as a Python library).


Known issues
============

* In Windows, the scripts are currently hard-coded to use FreeCAD from the default install directory for FreeCAD 0.14.

* The topography file is currently hard-coded to be the following format: a text file, one coordinate per line, with coordinates separated by semicolons.

Deployment
==========

The Python scripts have been tested in Debian jessie and Windows 7. They have the following dependencies:

* Python 2.7.9 (or later in the 2.7.* series)

* SciPy (at least the 0.14 version, since previous versions do not consistently orient faces in Delaunay triangulations).

* WxPython 3.0 (if using gui.py)

* If you are in windows and you decide to go for 64-bit, make sure to get a Python distribution that handles x64 properly, or download the python packages from www.lfd.uci.edu/~gohlke/pythonlibs

* FreeCAD (the scripts were developed with the 0.14 version, but any later version should be fine).

* You will also need to compile cork and place the binary in the same folder as the Python scripts (for ease of use, cork binaries for Windows are provided in releases).

Compiling cork in Linux is no big deal, just follow the instructions from gilbo's [repository](https://github.com/gilbo/cork) (or any fork you trust). However, in Windows, the history is a bit different. cork can be readily compiled in Visual Studio 2012 and later releases. However, you will also need a version of GMP compiled with exactly the same parameters. Now, GMP is easily built in POSIX machines, but not so easily in 
Windows ones. There is a fork of GMP with Windows support, MPIR, but it [does not work well for cork](https://github.com/gilbo/cork/issues/15). The alternative is to use CygWin to compile both GMP and cork, or cross-compile in POSIX for Windows. CygWin is a pain to install and configure, so I went for cross-compiling. However, cross-compiling is *also* a pain, and it turns out that it is a bit difficult to configure it properly and do the correct incantations in Debian: GMP cannot be easily compiled with clang because of errors in assembler code, apparently configured for gcc (ASM instructions can be disabled, but significant performance is lost in the process), but if compiled with gcc, it cannot be linked with code compiled in clang (required by cork) because gcc and clang differ in their exception handling methods. However, it is far easier in ArchLinux, as all the aforementioned problems are already solved. So I went for installing ArchLinux in a chroot of my Debian machine and cross-compiling sogilis' [fork](https://github.com/sogilis/cork), following instructions from [this comment](https://github.com/sogilis/cork/commit/b291e3dd9dffac95f14a7312e645357ccc1e5230#commitcomment-8948010). If you want to reproduce the build, this is my bash history in the ArchLinux chroot (be careful, it may contain errors, please also note that I unpackaged cork, mingw-w64-clang and mingw-w64-gmp in a custom directory of the chroot, /home/build):

```bash
pacman-key --init
pacman-key --populate archlinux
pacman -Syu
pacman -S base-devel --noconfirm
pacman -S mingw-w64-gcc --noconfirm
cd /home/build/mingw-w64-clang/
makepkg --asroot -s
pacman -U /home/build/mingw-w64-clang/mingw-w64-clang-r60.46ac262-1-x86_64.pkg.tar.xz
cd /home/build/mingw-w64-gmp/
makepkg --asroot -s
pacman -U /home/build/mingw-w64-gmp/mingw-w64-gmp-6.0.0-2-any.pkg.tar.xz
cd /home/build/cork
make CC=x86_64-w64-mingw32-clang CXX=x86_64-w64-mingw32-clang++ GMP_INC_DIR=/usr/x86_64-w64-mingw32/include/ GMP_LIB_DIR=/usr/x86_64-w64-mingw32/lib/
```

Licensing
=========

This software is licensed under the GPLv2.

