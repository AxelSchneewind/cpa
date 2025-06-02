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
    y_name=$(basename $y_file)

    # check existence
    [ -e $y_file ] || continue

    c_file=$(grep "input_files: '[^']*" "$y_file" | sed "s/input_files: '//" | sed "s/'//" | sed 's/\.i/.c/')
    c_file=${y_path}/${c_file}

    # check existence
    [ -e ${c_file} ] || continue

    # filter out files with gotos/switch: not supported
    ([ -n "$(grep -f blacklist-keywords.txt ${c_file})" ]) && continue
    #  && echo "skipping $c_file" && continue

    cp "$y_file" $benchset/
    cp "$c_file" $benchset/

    sed 's/\.c/.py/' -i $benchset/"$y_name"
    sed 's/\.i/.py/' -i $benchset/"$y_name"
done


# transform files
echo "Transpiling files from $benchset"
c_files=$benchset/*.c
for c_file in $c_files
do
    # prepare
    prepare_c "$c_file"
    fname=$(basename -s .c "$c_file")

    echo "transpiling $fname"
    $VENV_DIR/bin/python c2py "${benchset}/${fname}.c" "${benchset}/${fname}.py" 2> "${benchset}/error_${fname}"

    # 
    [ -n "$(cat $benchset/error_${fname})" ] && echo "error for ${fname}"
    [ -n "$(cat $benchset/error_${fname})" ] && [ -e "${benchset}/${fname}.py" ] && rm "${benchset}/${fname}.py"

    [ ! -e "${benchset}/${fname}.py" ] && rm ${benchset}/${fname}.yml

    # if empty, delete error file
    [ -n "$(cat ${benchset}/error_${fname})" ] || rm ${benchset}/error_${fname}

done

