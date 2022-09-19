#!/bin/sh

# c stands for clone. It clones git respositories easily to the work dir and opens it with an editor. Any Github link will work
# Example:
#    c https://github.com/InternalMD/Scripts/blob/master/BashUtils/load_functions.sh
c() (
    url="$1"

    # Find root dir for cloning repositories
    project_dir="$HOME"
    if [ -n "$PROJECT_DIR" ] && [ -d "$PROJECT_DIR" ]; then
        project_dir="$PROJECT_DIR"
    fi

    # Get base url
    url="$(echo "$1" | grep -oE "https?://github\.com/[^/]+/[^/]+")"
    if [ $? != 0 ]; then
        echo "ERROR: invalid url" >&2
        return 1
    fi

    # Clone
    repo_name="${url##*/}"
    repo_dir="$project_dir/$repo_name"
    if [ -d "$repo_dir" ]; then
        echo "WARNING: repo already cloned. Skipping"
    else
        git clone "$url.git" "$repo_dir"
        if [ $? != 0 ]; then
            echo "ERROR: could not clone" >&2
            return 1
        fi
    fi

    # Open in editor
    echo "Do you want to open $repo_dir?"
    echo "  1. VsCode"
    echo "  2. \$FILE_MANAGER ($FILE_MANAGER)"
    echo "  3. \$TERMINAL ($TERMINAL)"
    echo "  4. No"
    printf "Selection [1]: "
    read -r selection
    case "$selection" in
        2) $FILE_MANAGER "$repo_dir" & ;;
        3) $TERMINAL sh -c "cd $repo_dir; bash" & ;;
        4) ;;
        *) code "$repo_dir" & ;;
    esac
)
