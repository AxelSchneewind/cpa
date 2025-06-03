#!/bin/sh
VENV_DIR=../venv/ source ./prepare_c.sh

benchset="$(basename --suffix=.set $1)"
echo "Transforming set $benchset"


[ ! -e $benchset.set ] && echo "could not find benchset $1" && exit

if [ ! -e $benchset ]; then 
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
    
        c_file=$(grep "input_files: '[^']*" "${y_file}" | sed "s/input_files: '//" | sed "s/'//")
        c_file=${y_path}/${c_file}
    
        # check existence
        [ -e ${c_file} ] || continue
    
        # filter out files with gotos/switch: not supported
        ([ -z "$(grep -f blacklist-keywords.txt ${c_file})" ]) || continue
        #  && echo "skipping $c_file" && continue
    
        cp -r "$y_file" $benchset/
        cp -r "$c_file" $benchset/
    
        sed 's/\.c/.py/' -i "${benchset}/${y_name}"
        sed 's/\.i/.py/' -i "${benchset}/${y_name}"
    done
fi


# transform files
echo "Transpiling files from $benchset"
ls $benchset | wc
for y_file in $benchset/*.yml
do
    y_path=$(dirname $y_file)
    y_name=$(basename $y_file)

    c_file=$(grep "input_files: '[^']*" "${y_file}" | sed "s/input_files: '//" | sed "s/'//")
    echo $c_file
    c_file=${y_path}/${c_file}
    fname=$(basename -s .c "$c_file")
    fname=$(basename -s .i "$fname")

    [ ! -e "${benchset}/{fname}.py" ] || continue

    # prepare
    prepare_c "$c_file"

    echo "transpiling $fname"

    python c2py "${benchset}/${fname}.c" "$c_file" 2> "${benchset}/error_${fname}"

    # 
    [ ! -e "${benchset}/{fname}.py" ] || (python -m py_compile ${benchset}/${fname}.py || (echo 'invalid syntax' && rm -f  ${benchset}/${fname}.py))

    # 
    [ -n "$(cat $benchset/error_${fname})" ] && echo "error for ${fname}" && rm -f "${benchset}/${fname}.*"

    [ -e "${benchset}/${fname}.py" ] || rm ${benchset}/${fname}.yml

    # if empty, delete error file
    [ -n "$(cat ${benchset}/error_${fname})" ] || rm ${benchset}/error_${fname}

done

