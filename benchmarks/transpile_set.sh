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
    c_file="$(basename $line)"

    # filter out files with gotos/switch: not supported yet
    ([ -n "$(grep 'goto' $line)" ] || [ -n "$(grep 'switch' $line)" ]) && echo "skipping $line" && continue

    ln -sf "../$line" $benchset/

    cp "$line" "$tmp_dir/$c_file"
done


# transform files
echo "Transpiling files from $benchset"
tmp_files=$(echo $tmp_dir/*)
for file in $tmp_files
do
    c_file=$(basename $file)

    # prepare
    prepare_c "$tmp_dir/$c_file"

    echo "transpiling $c_file"

    # transform
    $VENV_DIR/bin/python c2py "${tmp_dir}/${c_file}" "$benchset/${c_file}.py" 2>$benchset/error_${c_file}
    ([ -n "$(cat $benchset/error_${c_file})" ] && echo "error for ${c_file}" && rm -f $benchset/${c_file}.py) || rm $benchset/error_${c_file}
done

rm -rf "$tmp_dir"

