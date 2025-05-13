#!/bin/sh

prepare_c() {
    local file="$1"

    # remove __assert_fail declaration
    sed -i -e 's/^.*extern\s*void\s*__assert_fail.*;//' "$file"

    # replace abort declaration
    sed -i -e 's/^.*extern\s*void\s*abort\s*{[^}]*}/void abort(void) { }/' "$file"

    # replace reach_error implementation
    sed -i -e 's/^\s*void\s*reach_error()\s{[^}]*}/void reach_error() {}/' "$file"

    # replace ERROR label and code block with reach_error call
    sed -i -e 's/\s*ERROR:\s*{[^}]*}/reach_error();/' "$file"

    # replace ERROR label and statement with reach_error call
    sed -i -e 's/\s*ERROR:\s*.*;/reach_error();/' "$file"

    # replace ERROR label with reach_error call
    sed -i -e 's/\s*ERROR:\s*/reach_error();/' "$file"
    
    # remove includes
    sed -i -e '/^\s*#\s*include.*$/d' "$file"
}

