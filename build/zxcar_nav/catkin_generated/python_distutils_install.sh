#!/bin/sh

if [ -n "$DESTDIR" ] ; then
    case $DESTDIR in
        /*) # ok
            ;;
        *)
            /bin/echo "DESTDIR argument must be absolute... "
            /bin/echo "otherwise python's distutils will bork things."
            exit 1
    esac
fi

echo_and_run() { echo "+ $@" ; "$@" ; }

echo_and_run cd "/home/sk/workspas/demo_zxcar/src/zxcar_nav"

# ensure that Python install destination exists
echo_and_run mkdir -p "$DESTDIR/home/sk/workspas/demo_zxcar/install/lib/python2.7/dist-packages"

# Note that PYTHONPATH is pulled from the environment to support installing
# into one location when some dependencies were installed in another
# location, #123.
echo_and_run /usr/bin/env \
    PYTHONPATH="/home/sk/workspas/demo_zxcar/install/lib/python2.7/dist-packages:/home/sk/workspas/demo_zxcar/build/lib/python2.7/dist-packages:$PYTHONPATH" \
    CATKIN_BINARY_DIR="/home/sk/workspas/demo_zxcar/build" \
    "/usr/bin/python2" \
    "/home/sk/workspas/demo_zxcar/src/zxcar_nav/setup.py" \
     \
    build --build-base "/home/sk/workspas/demo_zxcar/build/zxcar_nav" \
    install \
    --root="${DESTDIR-/}" \
    --install-layout=deb --prefix="/home/sk/workspas/demo_zxcar/install" --install-scripts="/home/sk/workspas/demo_zxcar/install/bin"
