#!/bin/sh

cfile="$1"
target="$2"
cname=$(basename --suffix=.c.prepared $cfile)
cpref=$(dirname $cfile)

[ -e $cfile ] || (echo "source file $cfile missing" && exit 1)

python ../c2py "${cfile}" "${target}" "$3"  2> "error_${cname}"

# remove empty error file
[ -n "$(cat error_${cname})" ] || rm error_${cname}
