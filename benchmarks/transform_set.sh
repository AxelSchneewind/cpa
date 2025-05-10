#!/bin/sh

VENV_DIR=../venv/

source ./prepare_c.sh

set="$(basename --suffix=.set $1)"
echo "Transforming set $set"

file=$(cat $set.set)
mkdir -p "tmp_$set" "$set"

# get files
for line in $file
do
    c_file="$(basename $line)"

    # filter out files with gotos: not supported yet
    [ ! -n "$(grep 'goto' $line)" ] && echo "skipping $line" && continue

    cp "$line" "tmp_$set/$c_file"
done

# transform files
tmp_files=$(echo tmp_$set/*)
for file in $tmp_files
do
    c_file=$(basename $file)

    # prepare
    prepare_c "tmp_$set/$c_file"

    # transform
    $VENV_DIR/bin/python c2py "tmp_$set/$c_file" "$set/$c_file.py" >/dev/null 2> /dev/null
done

rm -rf "tmp_$set"

