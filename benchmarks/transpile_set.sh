#!/bin/sh

VENV_DIR=../venv/

source ./prepare_c.sh

benchset="$(basename --suffix=.set $1)"
echo "Transforming set $benchset"


[ ! -e $benchset.set ] && echo "could not find benchset $1" && exit


tmp_dir="tmp_$benchset"
mkdir -p "$tmp_dir" 
mkdir -p "$benchset"

# get files
echo "Copying files from $benchset"

file=$(cat $benchset.set)
for line in $file
do
    y_file="$line"
    y_path=$(dirname $y_file)

    c_file=$(grep "input_files: '.*'" $y_file | sed "s/input_files: '//" | sed "s/'//")
    c_file=${y_path}/$c_file
    echo $c_file

    # filter out files with gotos/switch: not supported yet
    ([ -n "$(grep -f blacklist-keywords.txt $c_file)" ]) && echo "skipping $c_file" && continue

    cp "$y_file" $benchset/
    cp "$c_file" $benchset/
done


# transform files
echo "Transpiling files from $benchset"
c_files=$(echo $benchset/*.c)
for c_file in $c_files
do
    # prepare
    prepare_c "$c_file"
    fname=$(basename $c_file)

    echo "transpiling $c_file"

    # transform
    $VENV_DIR/bin/python c2py "${c_file}" "${c_file}.py" 2> $benchset/error_${fname}

    [ -n "$(cat $benchset/error_${fname})" ] && echo "error for ${fname}"
    [ -n "$(cat $benchset/error_${fname})" ] && rm -f $benchset/${fname}.py
    [ -n "$(cat $benchset/error_${fname})" ] && rm -f $benchset/${basename}.yml
    [ -n "$(cat $benchset/error_${fname})" ] || rm $benchset/error_${fname}

done

