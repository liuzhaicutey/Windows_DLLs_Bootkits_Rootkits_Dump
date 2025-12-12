#!/bin/bash
set -e
set +v

perl -pi -e 's/\r\n/\n/g' c_files_linux.txt
perl -pi -e 's/\r\n/\n/g' h_files.txt

CurDir=$PWD
GCC_FOLDER_NAME=/usr
BINUTILS_FOLDER_NAME=/usr

export PATH=$BINUTILS_FOLDER_NAME/bin:$PATH

cd ../Backend

rm -f objects.list

HFILES=-I$CurDir/inc/\ -I$CurDir/startup/

while read h; do
  HFILES="$HFILES -I$h"
done < "$CurDir/h_files.txt"

echo "--- Compiling Source Files ---"

while read f; do
    echo "Compiling $f..."
    "$GCC_FOLDER_NAME/bin/gcc" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -Og -ffreestanding -fshort-wchar -fpic -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-zero-initialized-in-bss -fno-common -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 $HFILES -g3 -Wall -Wextra -Wdouble-promotion -fmessage-length=0 -c -o "${f%.*}.o" "$f"
done < "$CurDir/c_files_linux.txt"

for f in "$CurDir/src"/*.c; do
    [ -f "$f" ] || continue
    echo "Compiling $f..."
    "$GCC_FOLDER_NAME/bin/gcc" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -Og -ffreestanding -fshort-wchar -fpic -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-zero-initialized-in-bss -fno-common -fno-exceptions -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 $HFILES -g3 -Wall -Wextra -Wdouble-promotion -Wpedantic -fmessage-length=0 -c -o "${f%.*}.o" "$f"
done

echo "--- Creating objects.list for Linker ---"

while read f; do
  echo "${f%.*}.o"
done < "$CurDir/c_files_linux.txt" > objects.list

for f in "$CurDir/src"/*.o; do
  [ -f "$f" ] && echo "$f"
done >> objects.list

echo "--- Linking BOOTX64.EFI (UEFI DLL) ---"

"$GCC_FOLDER_NAME/bin/gcc" -nostdlib -Wl,--warn-common -Wl,--no-undefined -Wl,-dll -Wl,--subsystem,10 -e efi_main -Wl,-Map=output.map -Wl,--image-base,0x400000 -Wl,--file-alignment,0x200 -Wl,--section-alignment,0x200 -o "BOOTX64.EFI" @"objects.list"

echo
echo "--- Printing size information ---"

"$BINUTILS_FOLDER_NAME/bin/size" "BOOTX64.EFI"
echo

cd "$CurDir"

read -p "Cleanup, recompile, or done? [c for cleanup, r for recompile, any other key for done] " UPL

echo
echo "**********************************************************"
echo

case "$UPL" in
  [cC])
    exec ./Cleanup.sh
  ;;
  [rR])
    exec ./Compile.sh
  ;;
  *)
  ;;
esac
