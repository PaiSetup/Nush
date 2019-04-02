function log() (
    git log --graph --pretty="format:%C(auto,yellow)%H %C(auto,green)%<(20,trunc)%aN %C(auto,cyan)%<(15,trunc)%cr %C(auto,reset)%s %C(auto)%d" $@
)
