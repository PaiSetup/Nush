function b() (
    mkdir -p build
    cd build
    cmake .. $@
)
