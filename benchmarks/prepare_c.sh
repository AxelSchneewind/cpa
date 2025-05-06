#!/bin/sh

prepare_c() {
local file="$1"
# replace ERROR label with reach_error call
sed -i -e 's/^.*ERROR:.*$/\treach_error();/' "$file"
# remove abort declaration
sed -i -e 's/^.*extern\s*void\s*abort.*;/void abort(void) { }/' "$file"

# remove __assert_fail declaration
sed -i -e 's/^.*extern\s*void\s*__assert_fail.*;//' "$file"

# replace reach_error implementation
sed -i -e 's/^\s*void\s*reach_error().*$/void reach_error() {}/' "$file"
}

