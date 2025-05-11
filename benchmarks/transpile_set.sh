#!/bin/sh

VENV_DIR=../venv/

source ./prepare_c.sh

benchset="$(basename --suffix=.set $1)"
echo "Transforming set $benchset"

file=$(cat $benchset.set)
mkdir -p "tmp_$benchset" "$benchset"

# get files
for line in $file
do
    c_file="$(basename $line)"

    # filter out files with gotos: not supported yet
    [ -n "$(grep 'goto' $line)" ] && echo "skipping $line" && continue

    ln -s "../$line" $benchset/

    cp "$line" "tmp_$benchset/$c_file"
done

# transform files
tmp_files=$(echo tmp_$benchset/*)
for file in $tmp_files
do
    c_file=$(basename $file)

    # prepare
    prepare_c "tmp_$benchset/$c_file"

    echo "transpiling $c_file"

    # transform
    $VENV_DIR/bin/python c2py "tmp_$benchset/$c_file" "$benchset/$c_file.py" >/dev/null 2>/dev/null
    [ ! "$?"=="0" ] && rm tmp_$benchset/$c_file


done

rm -rf "tmp_$benchset"

