#!/usr/bin/sh

get_unmatching_packages() {
    file_expected="$(mktemp --suffix=".expected")"
    file_actual="$(mktemp --suffix=".actual")"

    printf "Gathering expected packages in $file_expected... "
    expected_packages="$($PAI_SETUP_ROOT/setup.py --list_packages)"
    if [ $? != 0 ]; then
        echo "Could not gather PaiSetup packages"
        return 1
    fi
    echo "$expected_packages" | sort | uniq | tee "$file_expected" | wc -l

    printf "Gathering actual packages in $file_actual... "
    yay -Qeq | sort | tee "$file_actual" | wc -l

    echo "diff \"$file_expected\" \"$file_actual\""
    diff "$file_expected" "$file_actual" --side-by-side --color=auto --suppress-common-lines

    echo "Removing tmp files"
    rm "$file_actual"
    rm "$file_expected"
}
