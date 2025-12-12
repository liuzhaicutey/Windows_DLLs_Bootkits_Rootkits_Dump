@echo off
setlocal ENABLEDELAYEDEXPANSION

rem --- Setup and Path Configuration ---
set CurDir=%CD%
set CurDir2=%CurDir:\=/%
set CurDir3=%CurDir2: =\ %
set GCC_FOLDER_NAME=mingw64

cd ../Backend

rem Set the PATH to include the GCC bin folder for access to gcc.exe
set PATH=%CD%\%GCC_FOLDER_NAME%\bin;%PATH%

rem Delete previous object list
del objects.list

rem --- Include File Setup ---
rem Two required include folders are always included, plus any from h_files.txt
set HFILES="-I%CurDir%\inc\" -I"%CurDir%\startup\"

FOR /F "tokens=*" %%h IN ('type "%CurDir%\h_files.txt"') DO set HFILES=!HFILES! -I"%%h"
set HFILES=%HFILES:\=/%

rem --- 1. Compilation Steps (.c / .s to .o) ---

echo.
echo =================================
echo Compiling Source Files (.c / .s)
echo =================================

rem Loop through and compile the backend .c files (listed in c_files_windows.txt)
FOR /F "tokens=*" %%f IN ('type "%CurDir%\c_files_windows.txt"') DO (
    echo Compiling %%~nf.c...
    "%GCC_FOLDER_NAME%\bin\gcc.exe" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -Og -ffreestanding -fshort-wchar -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-common -fno-zero-initialized-in-bss -fno-exceptions -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 -I!HFILES! -g3 -Wall -Wextra -Wdouble-promotion -fmessage-length=0 -c -o "%%~df%%~pf%%~nf.o" "%%~ff"
)

rem Compile the .c files in the startup folder
FOR %%f IN ("%CurDir2%/startup/*.c") DO (
    echo Compiling startup/%%~nf.c...
    "%GCC_FOLDER_NAME%\bin\gcc.exe" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -Og -ffreestanding -fshort-wchar -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-common -fno-zero-initialized-in-bss -fno-exceptions -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 -I!HFILES! -g3 -Wall -Wextra -Wdouble-promotion -Wpedantic -fmessage-length=0 -c -o "%CurDir2%/startup/%%~nf.o" "%CurDir2%/startup/%%~nf.c"
)

rem Compile the .s files (assembly) in the startup folder
FOR %%f IN ("%CurDir2%/startup/*.s") DO (
    echo Compiling startup/%%~nf.s...
    "%GCC_FOLDER_NAME%\bin\gcc.exe" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -ffreestanding -fshort-wchar -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-common -fno-zero-initialized-in-bss -fno-exceptions -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 -I"%CurDir2%/inc/" -g -o "%CurDir2%/startup/%%~nf.o" "%CurDir2%/startup/%%~nf.s"
)

rem Compile user .c file (Bootloader.c)
echo Compiling src/Bootloader.c...
"%GCC_FOLDER_NAME%\bin\gcc.exe" -DGNU_EFI_USE_MS_ABI -mno-avx -mcmodel=small -mno-stack-arg-probe -m64 -mno-red-zone -maccumulate-outgoing-args -Og -ffreestanding -fshort-wchar -fomit-frame-pointer -fno-delete-null-pointer-checks -fno-common -fno-zero-initialized-in-bss -fno-exceptions -fno-stack-protector -fno-stack-check -fno-strict-aliasing -fno-merge-all-constants -fno-merge-constants --std=c11 -I%HFILES% -g3 -Wall -Wextra -Wdouble-promotion -Wpedantic -fmessage-length=0 -c -o "%CurDir2%/src/Bootloader.o" "%CurDir2%/src/Bootloader.c"

rem --- 2. Object List Creation (Consolidate .o files for the Linker) ---

echo.
echo =================================
echo Creating objects.list for Linker
echo =================================

rem Create OBJECTS variable (for slash conversion)
set OBJECTS=

rem Add compiled Backend .o files
FOR /F "tokens=*" %%f IN ('type "%CurDir%\c_files_windows.txt"') DO (
    set OBJECTS="%%~df%%~pf%%~nf.o"
    set OBJECTS=!OBJECTS:\=/!
    set OBJECTS=!OBJECTS: =\ !
    set OBJECTS=!OBJECTS:"\ \ ="!
    echo !OBJECTS! >> objects.list
)

rem Add compiled .o files from the startup directory
FOR %%f IN ("%CurDir2%/startup/*.o") DO echo "%CurDir3%/startup/%%~nxf" >> objects.list

rem Add compiled user .o files
echo "%CurDir3%/src/Bootloader.o" >> objects.list

rem --- 3. Linking into BOOTX64.EFI (The UEFI DLL) ---

echo.
echo =================================
echo Linking BOOTX64.EFI (UEFI DLL)
echo =================================

"%GCC_FOLDER_NAME%\bin\gcc.exe" -nostdlib -Wl,--warn-common -Wl,--no-undefined -Wl,-dll -Wl,--subsystem,10 -e efi_main -Wl,-Map=output.map -Wl,--image-base,0x400000 -Wl,--file-alignment,0x200 -Wl,--section-alignment,0x200 -o "BOOTX64.EFI" @"objects.list"

rem --- Final Output ---

echo.
echo Generating binary and Printing size information:
echo.
"%GCC_FOLDER_NAME%\bin\size.exe" "BOOTX64.EFI"
echo.

rem Return to the folder started from and exit
endlocal
